from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.analysis.liquidity_profile import calculate_liquidity_profile
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class AdaptiveExecutionSlice:
    sequence: int
    action: str
    quantity: float
    liquidity_distance_bps: float
    max_impact_percent: float
    max_spread_percent: float


@dataclass(frozen=True)
class AdaptiveExecutionPlan:
    exchange: str
    symbol: str
    action: str

    requested_quantity: float
    planned_quantity: float
    remaining_quantity: float

    slice_count: int
    slices: list[AdaptiveExecutionSlice]

    available_liquidity: float
    liquidity_utilization_percent: float

    reason: str
    created_at: datetime

    @property
    def is_complete(self) -> bool:
        return self.remaining_quantity <= 1e-12

    @property
    def is_actionable(self) -> bool:
        return self.planned_quantity > 0 and self.slice_count > 0


class AdaptiveExecutionPlanner:
    """
    Research-grade adaptive execution planner.

    Unlike a fixed-size execution planner, this planner examines
    the current visible order-book liquidity and creates child
    orders based on available depth.

    This component does NOT place real orders.
    """

    EPSILON = 1e-12

    def __init__(
        self,
        liquidity_utilization: float = 0.10,
        max_slices: int = 20,
        minimum_slice_quantity: float = 0.01,
        liquidity_distance_bps: float = 10.0,
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

        if minimum_slice_quantity <= 0:
            raise ValueError(
                "minimum_slice_quantity must be greater than zero"
            )

        if liquidity_distance_bps <= 0:
            raise ValueError(
                "liquidity_distance_bps must be greater than zero"
            )

        self.liquidity_utilization = float(liquidity_utilization)
        self.max_slices = int(max_slices)
        self.minimum_slice_quantity = float(minimum_slice_quantity)
        self.liquidity_distance_bps = float(liquidity_distance_bps)

    def create_plan(
        self,
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> AdaptiveExecutionPlan:

        self._validate_inputs(
            order_book,
            decision,
            risk_assessment,
        )

        if decision.action not in {"BUY", "SELL"}:
            return self._empty_plan(
                order_book=order_book,
                decision=decision,
                risk_assessment=risk_assessment,
                reason="execution decision is not actionable",
            )

        if not risk_assessment.approved:
            return self._empty_plan(
                order_book=order_book,
                decision=decision,
                risk_assessment=risk_assessment,
                reason="risk assessment did not approve the order",
            )

        allowed_quantity = min(
            risk_assessment.allowed_quantity,
            risk_assessment.requested_quantity,
        )

        if allowed_quantity <= self.EPSILON:
            return self._empty_plan(
                order_book=order_book,
                decision=decision,
                risk_assessment=risk_assessment,
                reason="risk assessment allowed zero quantity",
            )

        profile = calculate_liquidity_profile(
            order_book,
            distances_bps=(
                1.0,
                2.0,
                5.0,
                self.liquidity_distance_bps,
            ),
        )

        available_liquidity = self._available_liquidity(
            order_book=order_book,
            action=decision.action,
            distance_bps=self.liquidity_distance_bps,
        )

        if available_liquidity <= self.EPSILON:
            return self._empty_plan(
                order_book=order_book,
                decision=decision,
                risk_assessment=risk_assessment,
                reason="no visible liquidity available within configured distance",
            )

        target_quantity = min(
            allowed_quantity,
            available_liquidity * self.liquidity_utilization,
        )

        if target_quantity <= self.EPSILON:
            return self._empty_plan(
                order_book=order_book,
                decision=decision,
                risk_assessment=risk_assessment,
                reason="adaptive liquidity limit produced zero quantity",
            )

        slice_count = min(
            self.max_slices,
            max(
                1,
                int(
                    -(
                        -target_quantity
                        // max(
                            self.minimum_slice_quantity,
                            target_quantity / self.max_slices,
                        )
                    )
                ),
            ),
        )

        slice_count = max(
            1,
            min(
                self.max_slices,
                slice_count,
            ),
        )

        child_quantity = target_quantity / slice_count

        slices: list[AdaptiveExecutionSlice] = []

        for sequence in range(1, slice_count + 1):
            slices.append(
                AdaptiveExecutionSlice(
                    sequence=sequence,
                    action=decision.action,
                    quantity=child_quantity,
                    liquidity_distance_bps=self.liquidity_distance_bps,
                    max_impact_percent=risk_assessment.market_impact_percent,
                    max_spread_percent=risk_assessment.spread_percent,
                )
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

        if available_liquidity > self.EPSILON:
            utilization_percent = (
                planned_quantity
                / available_liquidity
            ) * 100.0
        else:
            utilization_percent = 0.0

        return AdaptiveExecutionPlan(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=risk_assessment.requested_quantity,
            planned_quantity=planned_quantity,
            remaining_quantity=remaining_quantity,
            slice_count=len(slices),
            slices=slices,
            available_liquidity=available_liquidity,
            liquidity_utilization_percent=utilization_percent,
            reason="adaptive execution plan created",
            created_at=datetime.now(timezone.utc),
        )

    def _available_liquidity(
        self,
        order_book: OrderBook,
        action: str,
        distance_bps: float,
    ) -> float:

        mid_price = (
            order_book.best_bid.price
            + order_book.best_ask.price
        ) / 2.0

        if mid_price <= self.EPSILON:
            return 0.0

        distance_ratio = distance_bps / 10_000.0

        if action == "BUY":
            maximum_price = mid_price * (
                1.0 + distance_ratio
            )

            return sum(
                level.quantity
                for level in order_book.asks
                if level.price <= maximum_price
                and level.quantity > 0
            )

        if action == "SELL":
            minimum_price = mid_price * (
                1.0 - distance_ratio
            )

            return sum(
                level.quantity
                for level in order_book.bids
                if level.price >= minimum_price
                and level.quantity > 0
            )

        return 0.0

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
        order_book: OrderBook,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
        reason: str,
    ) -> AdaptiveExecutionPlan:

        return AdaptiveExecutionPlan(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=risk_assessment.requested_quantity,
            planned_quantity=0.0,
            remaining_quantity=risk_assessment.requested_quantity,
            slice_count=0,
            slices=[],
            available_liquidity=0.0,
            liquidity_utilization_percent=0.0,
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )
