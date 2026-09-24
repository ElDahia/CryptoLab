from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.market_impact import simulate_market_order
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class AdaptiveExecutionSliceV4:
    sequence: int
    action: str
    quantity: float
    price_distance_bps: float
    source_liquidity: float
    utilization: float
    estimated_impact_percent: float
    estimated_slippage_percent: float
    max_impact_percent: float
    max_spread_percent: float


@dataclass(frozen=True)
class AdaptiveExecutionPlanV4:
    exchange: str
    symbol: str
    action: str
    requested_quantity: float
    planned_quantity: float
    remaining_quantity: float
    available_liquidity: float
    impact_limited_quantity: float
    slice_count: int
    slices: tuple[AdaptiveExecutionSliceV4, ...]
    max_impact_percent: float
    max_spread_percent: float
    reason: str
    created_at: datetime

    @property
    def average_slice_quantity(self) -> float:
        if not self.slices:
            return 0.0
        return self.planned_quantity / len(self.slices)

    @property
    def largest_slice_quantity(self) -> float:
        if not self.slices:
            return 0.0
        return max(item.quantity for item in self.slices)


class AdaptiveExecutionPlannerV4:
    """
    Impact-aware adaptive execution planner.

    Research/simulation only.
    No real orders are placed.

    The planner searches for the largest quantity that can be executed
    from the current visible order book without exceeding the configured
    market-impact limit.
    """

    def __init__(
        self,
        max_slices: int = 20,
        minimum_slice_quantity: float = 0.01,
        liquidity_distance_bps: float = 10.0,
        impact_search_iterations: int = 18,
    ) -> None:
        if max_slices <= 0:
            raise ValueError("max_slices must be greater than zero")

        if minimum_slice_quantity <= 0:
            raise ValueError("minimum_slice_quantity must be greater than zero")

        if liquidity_distance_bps <= 0:
            raise ValueError("liquidity_distance_bps must be greater than zero")

        if impact_search_iterations <= 0:
            raise ValueError(
                "impact_search_iterations must be greater than zero"
            )

        self.max_slices = max_slices
        self.minimum_slice_quantity = minimum_slice_quantity
        self.liquidity_distance_bps = liquidity_distance_bps
        self.impact_search_iterations = impact_search_iterations

    def create_plan(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> AdaptiveExecutionPlanV4:
        self._validate_inputs(order_book, decision, risk_assessment)

        requested_quantity = risk_assessment.requested_quantity
        allowed_quantity = risk_assessment.allowed_quantity

        max_impact_percent = min(
            risk_assessment.market_impact_percent,
            decision.market_impact_percent
            if decision.market_impact_percent > 0
            else risk_assessment.market_impact_percent,
        )

        max_spread_percent = min(
            risk_assessment.spread_percent,
            decision.spread_percent
            if decision.spread_percent > 0
            else risk_assessment.spread_percent,
        )

        if not risk_assessment.approved:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "risk assessment did not approve the order",
            )

        if not decision.is_actionable:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "execution decision is not actionable",
            )

        if allowed_quantity <= 0:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "allowed quantity is zero",
            )

        if order_book.spread_percent > max_spread_percent:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "order-book spread exceeds execution limit",
            )

        available_liquidity = self._available_liquidity(
            order_book,
            decision.action,
        )

        if available_liquidity <= 0:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "no visible liquidity available within configured distance",
            )

        impact_limited_quantity = self._find_max_quantity_under_impact(
            order_book=order_book,
            action=decision.action,
            upper_bound=min(allowed_quantity, available_liquidity),
            max_impact_percent=max_impact_percent,
        )

        planned_quantity = min(
            allowed_quantity,
            impact_limited_quantity,
            available_liquidity,
        )

        if planned_quantity < self.minimum_slice_quantity:
            return self._empty_plan(
                order_book,
                decision,
                requested_quantity,
                max_impact_percent,
                max_spread_percent,
                "impact-aware capacity is below minimum slice quantity",
                available_liquidity=available_liquidity,
                impact_limited_quantity=impact_limited_quantity,
            )

        slices = self._build_slices(
            order_book=order_book,
            action=decision.action,
            planned_quantity=planned_quantity,
            max_impact_percent=max_impact_percent,
            max_spread_percent=max_spread_percent,
        )

        actual_planned_quantity = sum(item.quantity for item in slices)

        return AdaptiveExecutionPlanV4(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            action=decision.action,
            requested_quantity=requested_quantity,
            planned_quantity=actual_planned_quantity,
            remaining_quantity=max(
                0.0,
                requested_quantity - actual_planned_quantity,
            ),
            available_liquidity=available_liquidity,
            impact_limited_quantity=impact_limited_quantity,
            slice_count=len(slices),
            slices=tuple(slices),
            max_impact_percent=max_impact_percent,
            max_spread_percent=max_spread_percent,
            reason="impact-aware adaptive execution plan created",
            created_at=datetime.now(timezone.utc),
        )

    def _find_max_quantity_under_impact(
        self,
        order_book: OrderBook,
        action: str,
        upper_bound: float,
        max_impact_percent: float,
    ) -> float:
        if upper_bound <= 0:
            return 0.0

        low = 0.0
        high = upper_bound

        for _ in range(self.impact_search_iterations):
            midpoint = (low + high) / 2.0

            if midpoint <= 0:
                break

            result = simulate_market_order(
                order_book=order_book,
                side=action,
                quantity=midpoint,
            )

            if not result.fully_filled:
                high = midpoint
                continue

            if result.price_impact_percent <= max_impact_percent:
                low = midpoint
            else:
                high = midpoint

        return low

    def _available_liquidity(
        self,
        order_book: OrderBook,
        action: str,
    ) -> float:
        reference_price = (
            order_book.best_ask.price
            if action == "BUY"
            else order_book.best_bid.price
        )

        levels = (
            order_book.asks
            if action == "BUY"
            else order_book.bids
        )

        total = 0.0

        for level in levels:
            distance_bps = (
                abs(level.price - reference_price)
                / reference_price
                * 10000
            )

            if distance_bps > self.liquidity_distance_bps:
                continue

            total += level.quantity

        return total

    def _build_slices(
        self,
        order_book: OrderBook,
        action: str,
        planned_quantity: float,
        max_impact_percent: float,
        max_spread_percent: float,
    ) -> list[AdaptiveExecutionSliceV4]:
        levels = (
            order_book.asks
            if action == "BUY"
            else order_book.bids
        )

        reference_price = (
            order_book.best_ask.price
            if action == "BUY"
            else order_book.best_bid.price
        )

        eligible_levels = []

        for level in levels:
            distance_bps = (
                abs(level.price - reference_price)
                / reference_price
                * 10000
            )

            if distance_bps <= self.liquidity_distance_bps:
                eligible_levels.append((level, distance_bps))

        if not eligible_levels:
            return []

        bucket_count = min(
            self.max_slices,
            len(eligible_levels),
        )

        buckets: list[list[tuple[object, float]]] = [
            [] for _ in range(bucket_count)
        ]

        for index, item in enumerate(eligible_levels):
            bucket_index = min(
                index * bucket_count // len(eligible_levels),
                bucket_count - 1,
            )

            buckets[bucket_index].append(item)

        slices: list[AdaptiveExecutionSliceV4] = []
        remaining = planned_quantity

        for bucket in buckets:
            if remaining <= 0:
                break

            source_liquidity = sum(
                level.quantity
                for level, _ in bucket
            )

            if source_liquidity <= 0:
                continue

            candidate = min(
                remaining,
                source_liquidity,
            )

            prefix_book = self._build_prefix_book(
                order_book,
                action,
                bucket,
            )

            safe_quantity = self._find_max_quantity_under_impact(
                order_book=prefix_book,
                action=action,
                upper_bound=candidate,
                max_impact_percent=max_impact_percent,
            )

            quantity = min(
                candidate,
                safe_quantity,
            )

            if quantity < self.minimum_slice_quantity:
                continue

            impact_result = simulate_market_order(
                order_book=prefix_book,
                side=action,
                quantity=quantity,
            )

            distance_bps = max(
                item[1]
                for item in bucket
            )

            utilization = quantity / source_liquidity

            slices.append(
                AdaptiveExecutionSliceV4(
                    sequence=len(slices) + 1,
                    action=action,
                    quantity=quantity,
                    price_distance_bps=distance_bps,
                    source_liquidity=source_liquidity,
                    utilization=utilization,
                    estimated_impact_percent=(
                        impact_result.price_impact_percent
                    ),
                    estimated_slippage_percent=(
                        impact_result.slippage_percent
                    ),
                    max_impact_percent=max_impact_percent,
                    max_spread_percent=max_spread_percent,
                )
            )

            remaining -= quantity

        return slices

    def _build_prefix_book(
        self,
        order_book: OrderBook,
        action: str,
        bucket: list[tuple[object, float]],
    ) -> OrderBook:
        allowed_prices = {
            level.price
            for level, _ in bucket
        }

        if action == "BUY":
            asks = [
                level
                for level in order_book.asks
                if level.price in allowed_prices
            ]

            bids = order_book.bids
        else:
            bids = [
                level
                for level in order_book.bids
                if level.price in allowed_prices
            ]

            asks = order_book.asks

        return OrderBook(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            bids=bids,
            asks=asks,
            received_at=order_book.received_at,
        )

    def _validate_inputs(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> None:
        if order_book.exchange != decision.exchange:
            raise ValueError("exchange mismatch")

        if order_book.symbol != decision.symbol:
            raise ValueError("symbol mismatch")

        if risk_assessment.exchange != decision.exchange:
            raise ValueError("risk exchange mismatch")

        if risk_assessment.symbol != decision.symbol:
            raise ValueError("risk symbol mismatch")

        if decision.action not in {"BUY", "SELL"}:
            raise ValueError("decision action must be BUY or SELL")

        if risk_assessment.requested_quantity < 0:
            raise ValueError("requested quantity must not be negative")

    def _empty_plan(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        requested_quantity: float,
        max_impact_percent: float,
        max_spread_percent: float,
        reason: str,
        available_liquidity: float = 0.0,
        impact_limited_quantity: float = 0.0,
    ) -> AdaptiveExecutionPlanV4:
        return AdaptiveExecutionPlanV4(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            action=decision.action,
            requested_quantity=requested_quantity,
            planned_quantity=0.0,
            remaining_quantity=requested_quantity,
            available_liquidity=available_liquidity,
            impact_limited_quantity=impact_limited_quantity,
            slice_count=0,
            slices=tuple(),
            max_impact_percent=max_impact_percent,
            max_spread_percent=max_spread_percent,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
