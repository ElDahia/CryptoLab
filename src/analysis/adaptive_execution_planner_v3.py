from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class AdaptiveExecutionSliceV3:
    sequence: int
    action: str
    quantity: float
    source_liquidity: float
    price_distance_bps: float
    liquidity_utilization_percent: float
    max_impact_percent: float
    max_spread_percent: float


@dataclass(frozen=True)
class AdaptiveExecutionPlanV3:
    exchange: str
    symbol: str
    action: str

    requested_quantity: float
    planned_quantity: float
    remaining_quantity: float

    available_liquidity: float
    capacity_quantity: float

    slice_count: int
    slices: list[AdaptiveExecutionSliceV3]

    utilization_percent: float
    average_slice_quantity: float
    largest_slice_quantity: float

    reason: str
    created_at: datetime

    @property
    def is_complete(self) -> bool:
        return self.remaining_quantity <= 1e-12

    @property
    def is_actionable(self) -> bool:
        return self.planned_quantity > 0 and self.slice_count > 0


class AdaptiveExecutionPlannerV3:
    """
    Liquidity-curve adaptive execution planner.

    V3 groups nearby order-book liquidity into execution buckets
    instead of treating every individual order-book level as a
    separate child order.

    The planner never creates quantity above visible liquidity.

    This component does NOT place real orders.
    """

    EPSILON = 1e-12

    def __init__(
        self,
        liquidity_utilization: float = 0.10,
        max_slices: int = 20,
        liquidity_distance_bps: float = 10.0,
        minimum_slice_quantity: float = 0.01,
    ) -> None:

        if not 0 < liquidity_utilization <= 1:
            raise ValueError(
                "liquidity_utilization must be greater than zero "
                "and less than or equal to one"
            )

        if max_slices <= 0:
            raise ValueError(
                "max_slices must be greater than zero"
            )

        if liquidity_distance_bps <= 0:
            raise ValueError(
                "liquidity_distance_bps must be greater than zero"
            )

        if minimum_slice_quantity <= 0:
            raise ValueError(
                "minimum_slice_quantity must be greater than zero"
            )

        self.liquidity_utilization = float(liquidity_utilization)
        self.max_slices = int(max_slices)
        self.liquidity_distance_bps = float(liquidity_distance_bps)
        self.minimum_slice_quantity = float(minimum_slice_quantity)

    def create_plan(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> AdaptiveExecutionPlanV3:

        self._validate_inputs(
            order_book,
            decision,
            risk_assessment,
        )

        if decision.action not in {"BUY", "SELL"}:
            return self._empty_plan(
                decision,
                risk_assessment,
                "execution decision is not actionable",
            )

        if not risk_assessment.approved:
            return self._empty_plan(
                decision,
                risk_assessment,
                "risk assessment did not approve the order",
            )

        allowed_quantity = min(
            risk_assessment.allowed_quantity,
            risk_assessment.requested_quantity,
        )

        if allowed_quantity <= self.EPSILON:
            return self._empty_plan(
                decision,
                risk_assessment,
                "risk assessment allowed zero quantity",
            )

        levels = self._eligible_levels(
            order_book,
            decision.action,
        )

        if not levels:
            return self._empty_plan(
                decision,
                risk_assessment,
                "no visible liquidity within configured distance",
            )

        available_liquidity = sum(
            level["quantity"]
            for level in levels
        )

        capacity_quantity = min(
            allowed_quantity,
            available_liquidity * self.liquidity_utilization,
        )

        if capacity_quantity <= self.EPSILON:
            return self._empty_plan(
                decision,
                risk_assessment,
                "adaptive liquidity capacity is zero",
            )

        buckets = self._build_buckets(
            levels,
            self.max_slices,
        )

        slices = self._build_slices(
            buckets=buckets,
            capacity_quantity=capacity_quantity,
            decision=decision,
            risk_assessment=risk_assessment,
        )

        planned_quantity = sum(
            execution_slice.quantity
            for execution_slice in slices
        )

        remaining_quantity = max(
            0.0,
            risk_assessment.requested_quantity
            - planned_quantity,
        )

        utilization_percent = (
            planned_quantity / available_liquidity
        ) * 100.0

        quantities = [
            execution_slice.quantity
            for execution_slice in slices
        ]

        average_slice_quantity = (
            sum(quantities) / len(quantities)
            if quantities
            else 0.0
        )

        largest_slice_quantity = (
            max(quantities)
            if quantities
            else 0.0
        )

        return AdaptiveExecutionPlanV3(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=risk_assessment.requested_quantity,
            planned_quantity=planned_quantity,
            remaining_quantity=remaining_quantity,
            available_liquidity=available_liquidity,
            capacity_quantity=capacity_quantity,
            slice_count=len(slices),
            slices=slices,
            utilization_percent=utilization_percent,
            average_slice_quantity=average_slice_quantity,
            largest_slice_quantity=largest_slice_quantity,
            reason="liquidity-curve adaptive execution plan created",
            created_at=datetime.now(timezone.utc),
        )

    def _eligible_levels(
        self,
        order_book: OrderBook,
        action: str,
    ) -> list[dict[str, float]]:

        mid_price = (
            order_book.best_bid.price
            + order_book.best_ask.price
        ) / 2.0

        if mid_price <= self.EPSILON:
            return []

        distance_ratio = (
            self.liquidity_distance_bps
            / 10_000.0
        )

        if action == "BUY":

            maximum_price = mid_price * (
                1.0 + distance_ratio
            )

            eligible = [
                level
                for level in order_book.asks
                if level.quantity > self.EPSILON
                and level.price <= maximum_price
            ]

            eligible.sort(
                key=lambda level: level.price
            )

        elif action == "SELL":

            minimum_price = mid_price * (
                1.0 - distance_ratio
            )

            eligible = [
                level
                for level in order_book.bids
                if level.quantity > self.EPSILON
                and level.price >= minimum_price
            ]

            eligible.sort(
                key=lambda level: level.price,
                reverse=True,
            )

        else:
            return []

        result: list[dict[str, float]] = []

        for level in eligible:

            distance_bps = abs(
                (level.price - mid_price)
                / mid_price
            ) * 10_000.0

            result.append(
                {
                    "price": float(level.price),
                    "quantity": float(level.quantity),
                    "distance_bps": float(distance_bps),
                }
            )

        return result

    def _build_buckets(
        self,
        levels: list[dict[str, float]],
        bucket_count: int,
    ) -> list[list[dict[str, float]]]:

        if not levels:
            return []

        bucket_count = min(
            bucket_count,
            len(levels),
        )

        buckets: list[list[dict[str, float]]] = [
            []
            for _ in range(bucket_count)
        ]

        for index, level in enumerate(levels):

            bucket_index = min(
                bucket_count - 1,
                int(
                    index
                    * bucket_count
                    / len(levels)
                ),
            )

            buckets[bucket_index].append(level)

        return [
            bucket
            for bucket in buckets
            if bucket
        ]

    def _build_slices(
        self,
        buckets: list[list[dict[str, float]]],
        capacity_quantity: float,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> list[AdaptiveExecutionSliceV3]:

        if not buckets:
            return []

        total_bucket_liquidity = [
            sum(
                level["quantity"]
                for level in bucket
            )
            for bucket in buckets
        ]

        total_liquidity = sum(
            total_bucket_liquidity
        )

        if total_liquidity <= self.EPSILON:
            return []

        remaining_capacity = capacity_quantity
        slices: list[AdaptiveExecutionSliceV3] = []

        for bucket, bucket_liquidity in zip(
            buckets,
            total_bucket_liquidity,
        ):

            if remaining_capacity <= self.EPSILON:
                break

            if len(slices) >= self.max_slices:
                break

            if bucket_liquidity <= self.EPSILON:
                continue

            proportional_quantity = (
                capacity_quantity
                * bucket_liquidity
                / total_liquidity
            )

            slice_quantity = min(
                proportional_quantity,
                bucket_liquidity
                * self.liquidity_utilization,
                remaining_capacity,
            )

            if slice_quantity < self.minimum_slice_quantity:
                continue

            distance_bps = max(
                level["distance_bps"]
                for level in bucket
            )

            utilization_percent = (
                slice_quantity
                / bucket_liquidity
            ) * 100.0

            slices.append(
                AdaptiveExecutionSliceV3(
                    sequence=len(slices) + 1,
                    action=decision.action,
                    quantity=slice_quantity,
                    source_liquidity=bucket_liquidity,
                    price_distance_bps=distance_bps,
                    liquidity_utilization_percent=utilization_percent,
                    max_impact_percent=risk_assessment.market_impact_percent,
                    max_spread_percent=risk_assessment.spread_percent,
                )
            )

            remaining_capacity -= slice_quantity

        return slices

    def _validate_inputs(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> None:

        if order_book.exchange != decision.exchange:
            raise ValueError(
                "Order book and execution decision exchanges must match"
            )

        if order_book.symbol != decision.symbol:
            raise ValueError(
                "Order book and execution decision symbols must match"
            )

        if decision.exchange != risk_assessment.exchange:
            raise ValueError(
                "Execution decision and risk assessment exchanges must match"
            )

        if decision.symbol != risk_assessment.symbol:
            raise ValueError(
                "Execution decision and risk assessment symbols must match"
            )

    def _empty_plan(
        self,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
        reason: str,
    ) -> AdaptiveExecutionPlanV3:

        return AdaptiveExecutionPlanV3(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=risk_assessment.requested_quantity,
            planned_quantity=0.0,
            remaining_quantity=risk_assessment.requested_quantity,
            available_liquidity=0.0,
            capacity_quantity=0.0,
            slice_count=0,
            slices=[],
            utilization_percent=0.0,
            average_slice_quantity=0.0,
            largest_slice_quantity=0.0,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
