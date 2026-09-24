from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_planner import ExecutionPlan
from src.analysis.market_impact import simulate_market_order
from src.exchanges.models import OrderBook, OrderBookLevel


@dataclass(frozen=True)
class DynamicSimulatedFill:
    sequence: int
    action: str
    requested_quantity: float
    filled_quantity: float
    unfilled_quantity: float
    average_execution_price: float
    reference_price: float
    slippage: float
    slippage_percent: float
    market_impact: float
    market_impact_percent: float
    total_notional: float
    levels_consumed: int
    fully_filled: bool


@dataclass(frozen=True)
class DynamicExecutionSimulationResult:
    exchange: str
    symbol: str
    action: str
    requested_quantity: float
    filled_quantity: float
    unfilled_quantity: float
    average_execution_price: float
    total_notional: float
    total_slippage: float
    total_slippage_percent: float
    total_market_impact: float
    total_market_impact_percent: float
    fully_filled: bool
    slice_count: int
    fills: tuple[DynamicSimulatedFill, ...]
    simulated_at: datetime

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0:
            return 0.0
        return self.filled_quantity / self.requested_quantity

    @property
    def is_complete(self) -> bool:
        return self.fully_filled and self.unfilled_quantity <= 0.0


class DynamicExecutionSimulatorV2:
    """
    Sequential execution simulator with a mutable local order book.

    Research/simulation only.
    No real orders are placed.

    Each execution slice consumes liquidity from the local book.
    The next slice therefore sees the remaining liquidity instead
    of the original static snapshot.
    """

    EPSILON = 1e-12

    def simulate(
        self,
        order_book: OrderBook,
        plan: ExecutionPlan,
    ) -> DynamicExecutionSimulationResult:
        self._validate_inputs(order_book, plan)

        bids = {
            level.price: level.quantity
            for level in order_book.bids
            if level.quantity > 0
        }

        asks = {
            level.price: level.quantity
            for level in order_book.asks
            if level.quantity > 0
        }

        fills: list[DynamicSimulatedFill] = []

        total_requested = plan.planned_quantity
        total_filled = 0.0
        total_notional = 0.0
        total_slippage = 0.0
        total_market_impact = 0.0

        for execution_slice in plan.slices:
            if execution_slice.quantity <= 0:
                continue

            remaining_liquidity = self._has_liquidity(
                action=execution_slice.action,
                bids=bids,
                asks=asks,
            )

            if not remaining_liquidity:
                break

            current_book = self._build_book(
                original=order_book,
                bids=bids,
                asks=asks,
            )

            result = simulate_market_order(
                order_book=current_book,
                side=execution_slice.action,
                quantity=execution_slice.quantity,
            )

            filled_quantity = result.filled_quantity

            if filled_quantity <= self.EPSILON:
                break

            self._consume_liquidity(
                action=execution_slice.action,
                execution_levels=result.execution_levels,
                bids=bids,
                asks=asks,
            )

            fill = DynamicSimulatedFill(
                sequence=execution_slice.sequence,
                action=execution_slice.action,
                requested_quantity=execution_slice.quantity,
                filled_quantity=filled_quantity,
                unfilled_quantity=max(
                    0.0,
                    execution_slice.quantity - filled_quantity,
                ),
                average_execution_price=result.average_execution_price,
                reference_price=result.reference_price,
                slippage=result.slippage,
                slippage_percent=result.slippage_percent,
                market_impact=result.price_impact,
                market_impact_percent=result.price_impact_percent,
                total_notional=result.total_notional,
                levels_consumed=result.levels_consumed,
                fully_filled=result.fully_filled,
            )

            fills.append(fill)

            total_filled += filled_quantity
            total_notional += result.total_notional
            total_slippage += max(0.0, result.slippage)
            total_market_impact += max(0.0, result.price_impact)

            if not result.fully_filled:
                break

        unfilled_quantity = max(
            0.0,
            total_requested - total_filled,
        )

        average_execution_price = (
            total_notional / total_filled
            if total_filled > self.EPSILON
            else 0.0
        )

        reference_price = self._reference_price(
            order_book=order_book,
            action=plan.action,
        )

        total_slippage_percent = (
            total_slippage
            / reference_price
            / total_filled
            * 100
            if total_filled > self.EPSILON
            and reference_price > self.EPSILON
            else 0.0
        )

        total_market_impact_percent = (
            total_market_impact
            / reference_price
            / total_filled
            * 100
            if total_filled > self.EPSILON
            and reference_price > self.EPSILON
            else 0.0
        )

        return DynamicExecutionSimulationResult(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            action=plan.action,
            requested_quantity=total_requested,
            filled_quantity=total_filled,
            unfilled_quantity=unfilled_quantity,
            average_execution_price=average_execution_price,
            total_notional=total_notional,
            total_slippage=total_slippage,
            total_slippage_percent=total_slippage_percent,
            total_market_impact=total_market_impact,
            total_market_impact_percent=total_market_impact_percent,
            fully_filled=unfilled_quantity <= self.EPSILON,
            slice_count=len(fills),
            fills=tuple(fills),
            simulated_at=datetime.now(timezone.utc),
        )

    def _consume_liquidity(
        self,
        action: str,
        execution_levels,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> None:
        book_side = asks if action == "BUY" else bids

        for level in execution_levels:
            current_quantity = book_side.get(
                level.price,
                0.0,
            )

            remaining_quantity = (
                current_quantity - level.filled_quantity
            )

            if remaining_quantity <= self.EPSILON:
                book_side.pop(level.price, None)
            else:
                book_side[level.price] = remaining_quantity

    def _build_book(
        self,
        original: OrderBook,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> OrderBook:
        return OrderBook(
            exchange=original.exchange,
            symbol=original.symbol,
            bids=[
                OrderBookLevel(
                    price=price,
                    quantity=quantity,
                )
                for price, quantity in bids.items()
                if quantity > self.EPSILON
            ],
            asks=[
                OrderBookLevel(
                    price=price,
                    quantity=quantity,
                )
                for price, quantity in asks.items()
                if quantity > self.EPSILON
            ],
            received_at=original.received_at,
        )

    def _has_liquidity(
        self,
        action: str,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> bool:
        if action == "BUY":
            return any(quantity > self.EPSILON for quantity in asks.values())

        return any(quantity > self.EPSILON for quantity in bids.values())

    def _reference_price(
        self,
        order_book: OrderBook,
        action: str,
    ) -> float:
        if action == "BUY":
            return order_book.best_ask.price

        return order_book.best_bid.price

    def _validate_inputs(
        self,
        order_book: OrderBook,
        plan: ExecutionPlan,
    ) -> None:
        if order_book.exchange != plan.exchange:
            raise ValueError("exchange mismatch")

        if order_book.symbol != plan.symbol:
            raise ValueError("symbol mismatch")

        if plan.action not in {"BUY", "SELL"}:
            raise ValueError("plan action must be BUY or SELL")

        if plan.planned_quantity < 0:
            raise ValueError("planned quantity must not be negative")

        if plan.slice_count != len(plan.slices):
            raise ValueError("slice count does not match slices")
