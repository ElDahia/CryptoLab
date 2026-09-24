from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_planner import ExecutionPlan, ExecutionSlice
from src.analysis.market_impact import MarketImpactResult, simulate_market_order
from src.exchanges.models import OrderBook, OrderBookLevel


@dataclass(frozen=True)
class SimulatedFill:
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

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0:
            return 0.0

        return self.filled_quantity / self.requested_quantity


@dataclass(frozen=True)
class ExecutionSimulationResult:
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
    fills: list[SimulatedFill]
    simulated_at: datetime

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0:
            return 0.0

        return self.filled_quantity / self.requested_quantity

    @property
    def is_complete(self) -> bool:
        return self.unfilled_quantity <= 1e-12


class ExecutionSimulator:
    """
    Sequential execution simulator.

    Each child order consumes liquidity from the same simulated
    order-book state. Liquidity consumed by an earlier slice is
    therefore unavailable to later slices.

    If the visible book is exhausted, the simulator returns a
    partial fill instead of raising an exception.

    This component does NOT place real orders.
    """

    EPSILON = 1e-12

    def simulate(
        self,
        order_book: OrderBook,
        plan: ExecutionPlan,
    ) -> ExecutionSimulationResult:
        self._validate_inputs(order_book, plan)

        if plan.slice_count == 0 or not plan.slices:
            return self._empty_result(plan)

        bids = {
            level.price: level.quantity
            for level in order_book.bids
            if level.quantity > self.EPSILON
        }

        asks = {
            level.price: level.quantity
            for level in order_book.asks
            if level.quantity > self.EPSILON
        }

        fills: list[SimulatedFill] = []

        total_filled = 0.0
        total_notional = 0.0

        weighted_slippage = 0.0
        weighted_impact = 0.0

        for execution_slice in plan.slices:
            if not self._has_liquidity(
                action=execution_slice.action,
                bids=bids,
                asks=asks,
            ):
                break

            simulated_book = self._build_book(
                order_book=order_book,
                bids=bids,
                asks=asks,
            )

            fill = self._simulate_slice(
                order_book=simulated_book,
                execution_slice=execution_slice,
            )

            self._consume_liquidity(
                action=execution_slice.action,
                filled_quantity=fill.filled_quantity,
                bids=bids,
                asks=asks,
            )

            fills.append(fill)

            total_filled += fill.filled_quantity
            total_notional += fill.total_notional

            weighted_slippage += (
                fill.slippage_percent * fill.filled_quantity
            )

            weighted_impact += (
                fill.market_impact_percent * fill.filled_quantity
            )

            if not fill.fully_filled:
                break

        unfilled_quantity = max(
            0.0,
            plan.requested_quantity - total_filled,
        )

        if total_filled > self.EPSILON:
            average_execution_price = (
                total_notional / total_filled
            )

            total_slippage_percent = (
                weighted_slippage / total_filled
            )

            total_market_impact_percent = (
                weighted_impact / total_filled
            )
        else:
            average_execution_price = 0.0
            total_slippage_percent = 0.0
            total_market_impact_percent = 0.0

        reference_price = self._reference_price(
            order_book=order_book,
            action=plan.action,
        )

        total_slippage = self._calculate_total_slippage(
            action=plan.action,
            average_execution_price=average_execution_price,
            reference_price=reference_price,
        )

        total_market_impact = (
            reference_price
            * total_market_impact_percent
            / 100.0
        )

        fully_filled = (
            unfilled_quantity <= self.EPSILON
            and total_filled > self.EPSILON
        )

        return ExecutionSimulationResult(
            exchange=plan.exchange,
            symbol=plan.symbol,
            action=plan.action,
            requested_quantity=plan.requested_quantity,
            filled_quantity=total_filled,
            unfilled_quantity=unfilled_quantity,
            average_execution_price=average_execution_price,
            total_notional=total_notional,
            total_slippage=total_slippage,
            total_slippage_percent=total_slippage_percent,
            total_market_impact=total_market_impact,
            total_market_impact_percent=total_market_impact_percent,
            fully_filled=fully_filled,
            slice_count=len(fills),
            fills=fills,
            simulated_at=datetime.now(timezone.utc),
        )

    def _simulate_slice(
        self,
        order_book: OrderBook,
        execution_slice: ExecutionSlice,
    ) -> SimulatedFill:
        result: MarketImpactResult = simulate_market_order(
            order_book=order_book,
            side=execution_slice.action,
            quantity=execution_slice.quantity,
        )

        return SimulatedFill(
            sequence=execution_slice.sequence,
            action=execution_slice.action,
            requested_quantity=result.requested_quantity,
            filled_quantity=result.filled_quantity,
            unfilled_quantity=result.unfilled_quantity,
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

    def _has_liquidity(
        self,
        action: str,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> bool:
        if action == "BUY":
            return any(
                quantity > self.EPSILON
                for quantity in asks.values()
            )

        if action == "SELL":
            return any(
                quantity > self.EPSILON
                for quantity in bids.values()
            )

        raise ValueError("Execution action must be BUY or SELL")

    def _consume_liquidity(
        self,
        action: str,
        filled_quantity: float,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> None:
        if filled_quantity <= self.EPSILON:
            return

        levels = asks if action == "BUY" else bids

        if action == "BUY":
            prices = sorted(levels.keys())
        elif action == "SELL":
            prices = sorted(levels.keys(), reverse=True)
        else:
            raise ValueError("Execution action must be BUY or SELL")

        remaining = filled_quantity

        for price in prices:
            if remaining <= self.EPSILON:
                break

            available = levels.get(price, 0.0)

            if available <= self.EPSILON:
                continue

            consumed = min(
                available,
                remaining,
            )

            remaining -= consumed

            new_quantity = available - consumed

            if new_quantity <= self.EPSILON:
                levels.pop(price, None)
            else:
                levels[price] = new_quantity

    def _build_book(
        self,
        order_book: OrderBook,
        bids: dict[float, float],
        asks: dict[float, float],
    ) -> OrderBook:
        return OrderBook(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
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
            received_at=order_book.received_at,
        )

    def _reference_price(
        self,
        order_book: OrderBook,
        action: str,
    ) -> float:
        if action == "BUY":
            return order_book.best_ask.price

        if action == "SELL":
            return order_book.best_bid.price

        raise ValueError("Execution action must be BUY or SELL")

    def _calculate_total_slippage(
        self,
        action: str,
        average_execution_price: float,
        reference_price: float,
    ) -> float:
        if (
            average_execution_price <= 0
            or reference_price <= 0
        ):
            return 0.0

        if action == "BUY":
            return max(
                0.0,
                average_execution_price - reference_price,
            )

        if action == "SELL":
            return max(
                0.0,
                reference_price - average_execution_price,
            )

        raise ValueError("Execution action must be BUY or SELL")

    def _validate_inputs(
        self,
        order_book: OrderBook,
        plan: ExecutionPlan,
    ) -> None:
        if order_book.exchange != plan.exchange:
            raise ValueError(
                "Order book and execution plan exchanges must match"
            )

        if order_book.symbol != plan.symbol:
            raise ValueError(
                "Order book and execution plan symbols must match"
            )

    def _empty_result(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionSimulationResult:
        return ExecutionSimulationResult(
            exchange=plan.exchange,
            symbol=plan.symbol,
            action=plan.action,
            requested_quantity=plan.requested_quantity,
            filled_quantity=0.0,
            unfilled_quantity=plan.requested_quantity,
            average_execution_price=0.0,
            total_notional=0.0,
            total_slippage=0.0,
            total_slippage_percent=0.0,
            total_market_impact=0.0,
            total_market_impact_percent=0.0,
            fully_filled=False,
            slice_count=0,
            fills=[],
            simulated_at=datetime.now(timezone.utc),
        )
