from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_decision import ExecutionDecision
from src.analysis.market_impact import simulate_market_order
from src.analysis.risk_engine import RiskAssessment
from src.exchanges.models import OrderBook, OrderBookLevel


EPSILON = 1e-12


@dataclass(frozen=True)
class AdaptiveExecutionSliceV5:
    sequence: int
    action: str
    quantity: float
    reference_price: float
    average_execution_price: float
    slippage_percent: float
    market_impact_percent: float
    levels_consumed: int
    remaining_quantity: float
    remaining_liquidity: float


@dataclass(frozen=True)
class AdaptiveExecutionResultV5:
    exchange: str
    symbol: str
    action: str

    requested_quantity: float
    planned_quantity: float
    filled_quantity: float
    unfilled_quantity: float

    average_execution_price: float
    total_notional: float

    total_slippage_percent: float
    total_market_impact_percent: float

    fully_filled: bool
    slice_count: int

    slices: tuple[AdaptiveExecutionSliceV5, ...]
    simulated_at: datetime

    @property
    def fill_ratio(self) -> float:
        if self.planned_quantity <= EPSILON:
            return 0.0

        return self.filled_quantity / self.planned_quantity

    @property
    def is_complete(self) -> bool:
        return self.fully_filled and self.unfilled_quantity <= EPSILON


class AdaptiveExecutionEngineV5:
    """
    Dynamic depth-aware adaptive execution simulator.

    Features:
    - Risk-aware planned quantity
    - Spread protection
    - Market-impact protection
    - Liquidity-aware sizing
    - Maximum liquidity utilization per slice
    - Maximum order-book levels per slice
    - Dynamic local order-book consumption
    - Recalculation after every slice
    - No overfill
    - No real exchange orders
    """

    def __init__(
        self,
        max_slices: int = 20,
        minimum_slice_quantity: float = 0.01,
        max_impact_percent: float = 0.05,
        max_spread_percent: float = 0.02,
        impact_search_iterations: int = 18,
        max_slice_fraction_of_liquidity: float = 0.25,
        max_levels_per_slice: int = 20,
    ) -> None:
        if max_slices <= 0:
            raise ValueError(
                "max_slices must be greater than zero"
            )

        if minimum_slice_quantity <= 0:
            raise ValueError(
                "minimum_slice_quantity must be greater than zero"
            )

        if max_impact_percent <= 0:
            raise ValueError(
                "max_impact_percent must be greater than zero"
            )

        if max_spread_percent <= 0:
            raise ValueError(
                "max_spread_percent must be greater than zero"
            )

        if impact_search_iterations <= 0:
            raise ValueError(
                "impact_search_iterations must be greater than zero"
            )

        if not 0 < max_slice_fraction_of_liquidity <= 1:
            raise ValueError(
                "max_slice_fraction_of_liquidity must be greater than zero "
                "and less than or equal to one"
            )

        if max_levels_per_slice <= 0:
            raise ValueError(
                "max_levels_per_slice must be greater than zero"
            )

        self.max_slices = max_slices
        self.minimum_slice_quantity = minimum_slice_quantity
        self.max_impact_percent = max_impact_percent
        self.max_spread_percent = max_spread_percent
        self.impact_search_iterations = impact_search_iterations
        self.max_slice_fraction_of_liquidity = (
            max_slice_fraction_of_liquidity
        )
        self.max_levels_per_slice = max_levels_per_slice

    def simulate(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> AdaptiveExecutionResultV5:

        self._validate_inputs(
            order_book,
            decision,
            risk_assessment,
        )

        requested_quantity = max(
            0.0,
            float(risk_assessment.requested_quantity),
        )

        if decision.action not in {"BUY", "SELL"}:
            return self._empty_result(
                order_book,
                decision.action,
                requested_quantity,
            )

        if decision.action != risk_assessment.action:
            return self._empty_result(
                order_book,
                decision.action,
                requested_quantity,
            )

        if not risk_assessment.approved:
            return self._empty_result(
                order_book,
                decision.action,
                requested_quantity,
            )

        planned_quantity = min(
            max(
                0.0,
                float(risk_assessment.allowed_quantity),
            ),
            requested_quantity,
        )

        if planned_quantity <= EPSILON:
            return self._empty_result(
                order_book,
                decision.action,
                requested_quantity,
            )

        if order_book.spread_percent > self.max_spread_percent:
            return self._empty_result(
                order_book,
                decision.action,
                requested_quantity,
            )

        bids = [
            OrderBookLevel(
                price=level.price,
                quantity=level.quantity,
            )
            for level in order_book.bids
            if level.quantity > EPSILON
        ]

        asks = [
            OrderBookLevel(
                price=level.price,
                quantity=level.quantity,
            )
            for level in order_book.asks
            if level.quantity > EPSILON
        ]

        remaining_quantity = planned_quantity

        total_filled = 0.0
        total_notional = 0.0

        execution_slices: list[AdaptiveExecutionSliceV5] = []

        for sequence in range(1, self.max_slices + 1):

            if remaining_quantity <= EPSILON:
                break

            current_book = self._build_remaining_book(
                order_book,
                bids,
                asks,
            )

            available_liquidity = self._available_liquidity(
                current_book,
                decision.action,
            )

            if available_liquidity <= EPSILON:
                break

            safe_quantity = self._find_safe_quantity(
                current_book,
                decision.action,
                remaining_quantity,
            )

            if safe_quantity <= EPSILON:
                break

            liquidity_cap = (
                available_liquidity
                * self.max_slice_fraction_of_liquidity
            )

            depth_cap = self._maximum_quantity_for_levels(
                current_book,
                decision.action,
                self.max_levels_per_slice,
            )

            slice_quantity = min(
                safe_quantity,
                liquidity_cap,
                depth_cap,
                remaining_quantity,
            )

            if (
                slice_quantity < self.minimum_slice_quantity
                and remaining_quantity > self.minimum_slice_quantity
            ):
                break

            execution_result = simulate_market_order(
                current_book,
                decision.action,
                slice_quantity,
            )

            if execution_result.filled_quantity <= EPSILON:
                break

            actual_filled = min(
                execution_result.filled_quantity,
                remaining_quantity,
            )

            actual_notional = (
                execution_result.average_execution_price
                * actual_filled
            )

            total_filled += actual_filled
            total_notional += actual_notional

            remaining_quantity = max(
                0.0,
                planned_quantity - total_filled,
            )

            self._consume_liquidity(
                bids=bids,
                asks=asks,
                action=decision.action,
                execution_result=execution_result,
            )

            remaining_liquidity = (
                self._available_liquidity_from_levels(
                    bids=bids,
                    asks=asks,
                    action=decision.action,
                )
            )

            execution_slices.append(
                AdaptiveExecutionSliceV5(
                    sequence=sequence,
                    action=decision.action,
                    quantity=actual_filled,
                    reference_price=(
                        execution_result.reference_price
                    ),
                    average_execution_price=(
                        execution_result.average_execution_price
                    ),
                    slippage_percent=(
                        execution_result.slippage_percent
                    ),
                    market_impact_percent=(
                        execution_result.price_impact_percent
                    ),
                    levels_consumed=(
                        execution_result.levels_consumed
                    ),
                    remaining_quantity=remaining_quantity,
                    remaining_liquidity=remaining_liquidity,
                )
            )

        fully_filled = remaining_quantity <= EPSILON

        unfilled_quantity = max(
            0.0,
            planned_quantity - total_filled,
        )

        if total_filled > EPSILON:

            average_execution_price = (
                total_notional / total_filled
            )

            reference_price = self._reference_price(
                order_book,
                decision.action,
            )

            total_slippage_percent = (
                self._aggregate_shortfall_percent(
                    reference_price,
                    average_execution_price,
                    decision.action,
                )
            )

            total_market_impact_percent = (
                total_slippage_percent
            )

        else:
            average_execution_price = 0.0
            total_slippage_percent = 0.0
            total_market_impact_percent = 0.0

        return AdaptiveExecutionResultV5(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            action=decision.action,
            requested_quantity=requested_quantity,
            planned_quantity=planned_quantity,
            filled_quantity=total_filled,
            unfilled_quantity=unfilled_quantity,
            average_execution_price=average_execution_price,
            total_notional=total_notional,
            total_slippage_percent=total_slippage_percent,
            total_market_impact_percent=total_market_impact_percent,
            fully_filled=fully_filled,
            slice_count=len(execution_slices),
            slices=tuple(execution_slices),
            simulated_at=datetime.now(timezone.utc),
        )

    def _find_safe_quantity(
        self,
        order_book: OrderBook,
        action: str,
        maximum_quantity: float,
    ) -> float:

        available_liquidity = self._available_liquidity(
            order_book,
            action,
        )

        upper_bound = min(
            maximum_quantity,
            available_liquidity,
        )

        if upper_bound <= EPSILON:
            return 0.0

        full_result = simulate_market_order(
            order_book,
            action,
            upper_bound,
        )

        if (
            full_result.fully_filled
            and full_result.price_impact_percent
            <= self.max_impact_percent
        ):
            return upper_bound

        low = 0.0
        high = upper_bound

        for _ in range(self.impact_search_iterations):

            midpoint = (low + high) / 2.0

            if midpoint <= EPSILON:
                break

            result = simulate_market_order(
                order_book,
                action,
                midpoint,
            )

            if (
                result.fully_filled
                and result.price_impact_percent
                <= self.max_impact_percent
            ):
                low = midpoint
            else:
                high = midpoint

        return low

    def _maximum_quantity_for_levels(
        self,
        order_book: OrderBook,
        action: str,
        maximum_levels: int,
    ) -> float:

        levels = (
            order_book.asks
            if action == "BUY"
            else order_book.bids
        )

        if not levels:
            return 0.0

        sorted_levels = sorted(
            levels,
            key=lambda level: level.price,
            reverse=action == "SELL",
        )

        selected_levels = sorted_levels[:maximum_levels]

        return sum(
            max(0.0, level.quantity)
            for level in selected_levels
        )

    def _consume_liquidity(
        self,
        bids: list[OrderBookLevel],
        asks: list[OrderBookLevel],
        action: str,
        execution_result,
    ) -> None:

        target_levels = (
            asks
            if action == "BUY"
            else bids
        )

        for execution_level in execution_result.execution_levels:

            remaining_to_consume = (
                execution_level.filled_quantity
            )

            if remaining_to_consume <= EPSILON:
                continue

            for index, level in enumerate(target_levels):

                if abs(
                    level.price - execution_level.price
                ) > EPSILON:
                    continue

                new_quantity = max(
                    0.0,
                    level.quantity - remaining_to_consume,
                )

                target_levels[index] = OrderBookLevel(
                    price=level.price,
                    quantity=new_quantity,
                )

                break

    def _build_remaining_book(
        self,
        original_book: OrderBook,
        bids: list[OrderBookLevel],
        asks: list[OrderBookLevel],
    ) -> OrderBook:

        return OrderBook(
            exchange=original_book.exchange,
            symbol=original_book.symbol,
            bids=[
                level
                for level in bids
                if level.quantity > EPSILON
            ],
            asks=[
                level
                for level in asks
                if level.quantity > EPSILON
            ],
            received_at=original_book.received_at,
        )

    def _available_liquidity(
        self,
        order_book: OrderBook,
        action: str,
    ) -> float:

        levels = (
            order_book.asks
            if action == "BUY"
            else order_book.bids
        )

        return sum(
            max(0.0, level.quantity)
            for level in levels
        )

    def _available_liquidity_from_levels(
        self,
        bids: list[OrderBookLevel],
        asks: list[OrderBookLevel],
        action: str,
    ) -> float:

        levels = asks if action == "BUY" else bids

        return sum(
            max(0.0, level.quantity)
            for level in levels
        )

    def _reference_price(
        self,
        order_book: OrderBook,
        action: str,
    ) -> float:

        if action == "BUY":
            return order_book.best_ask.price

        return order_book.best_bid.price

    def _aggregate_shortfall_percent(
        self,
        reference_price: float,
        average_execution_price: float,
        action: str,
    ) -> float:

        if reference_price <= EPSILON:
            return 0.0

        if action == "BUY":
            return (
                (
                    average_execution_price
                    - reference_price
                )
                / reference_price
            ) * 100.0

        return (
            (
                reference_price
                - average_execution_price
            )
            / reference_price
        ) * 100.0

    def _empty_result(
        self,
        order_book: OrderBook,
        action: str,
        requested_quantity: float,
    ) -> AdaptiveExecutionResultV5:

        return AdaptiveExecutionResultV5(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            action=action,
            requested_quantity=requested_quantity,
            planned_quantity=0.0,
            filled_quantity=0.0,
            unfilled_quantity=0.0,
            average_execution_price=0.0,
            total_notional=0.0,
            total_slippage_percent=0.0,
            total_market_impact_percent=0.0,
            fully_filled=False,
            slice_count=0,
            slices=tuple(),
            simulated_at=datetime.now(timezone.utc),
        )

    def _validate_inputs(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> None:

        if decision.exchange != order_book.exchange:
            raise ValueError(
                "decision exchange does not match order book exchange"
            )

        if decision.symbol != order_book.symbol:
            raise ValueError(
                "decision symbol does not match order book symbol"
            )

        if risk_assessment.exchange != order_book.exchange:
            raise ValueError(
                "risk assessment exchange does not match order book exchange"
            )

        if risk_assessment.symbol != order_book.symbol:
            raise ValueError(
                "risk assessment symbol does not match order book symbol"
            )

        if not order_book.bids or not order_book.asks:
            raise ValueError(
                "order book must contain both bids and asks"
            )