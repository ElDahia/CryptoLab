from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment


@dataclass(frozen=True)
class ExecutionSlice:
    sequence: int
    action: str
    quantity: float
    max_impact_percent: float
    max_spread_percent: float


@dataclass(frozen=True)
class ExecutionPlan:
    exchange: str
    symbol: str
    action: str
    requested_quantity: float
    planned_quantity: float
    remaining_quantity: float
    slice_count: int
    slices: list[ExecutionSlice]
    reason: str
    created_at: datetime

    @property
    def is_complete(self) -> bool:
        return self.remaining_quantity <= 1e-12

    @property
    def is_actionable(self) -> bool:
        return self.planned_quantity > 0 and self.slice_count > 0


class ExecutionPlanner:
    """
    Research-grade execution planner.

    Converts an approved risk assessment into a sequence of
    smaller child-order slices.

    This component does NOT place real orders.
    """

    EPSILON = 1e-12

    def __init__(
        self,
        default_slice_quantity: float = 1.0,
        max_slices: int = 20,
    ) -> None:
        if default_slice_quantity <= 0:
            raise ValueError("default_slice_quantity must be greater than zero")

        if max_slices <= 0:
            raise ValueError("max_slices must be greater than zero")

        self.default_slice_quantity = float(default_slice_quantity)
        self.max_slices = int(max_slices)

    def create_plan(
        self,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> ExecutionPlan:
        if decision.exchange != risk_assessment.exchange:
            raise ValueError("Decision and risk assessment exchanges must match")

        if decision.symbol != risk_assessment.symbol:
            raise ValueError("Decision and risk assessment symbols must match")

        if decision.action not in {"BUY", "SELL"}:
            return self._empty_plan(
                decision=decision,
                requested_quantity=risk_assessment.requested_quantity,
                reason="execution decision is not actionable",
            )

        if not risk_assessment.approved:
            return self._empty_plan(
                decision=decision,
                requested_quantity=risk_assessment.requested_quantity,
                reason="risk assessment did not approve the order",
            )

        if risk_assessment.allowed_quantity <= self.EPSILON:
            return self._empty_plan(
                decision=decision,
                requested_quantity=risk_assessment.requested_quantity,
                reason="risk assessment allowed zero quantity",
            )

        planned_quantity = min(
            risk_assessment.allowed_quantity,
            risk_assessment.requested_quantity,
        )

        slice_count = min(
            self.max_slices,
            max(
                1,
                int(
                    -(
                        -planned_quantity
                        // self.default_slice_quantity
                    )
                ),
            ),
        )

        child_quantity = planned_quantity / slice_count

        slices: list[ExecutionSlice] = []

        for sequence in range(1, slice_count + 1):
            slices.append(
                ExecutionSlice(
                    sequence=sequence,
                    action=decision.action,
                    quantity=child_quantity,
                    max_impact_percent=risk_assessment.market_impact_percent,
                    max_spread_percent=risk_assessment.spread_percent,
                )
            )

        actual_planned_quantity = sum(
            execution_slice.quantity for execution_slice in slices
        )

        remaining_quantity = max(
            0.0,
            risk_assessment.requested_quantity - actual_planned_quantity,
        )

        return ExecutionPlan(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=risk_assessment.requested_quantity,
            planned_quantity=actual_planned_quantity,
            remaining_quantity=remaining_quantity,
            slice_count=len(slices),
            slices=slices,
            reason="execution plan created",
            created_at=datetime.now(timezone.utc),
        )

    def _empty_plan(
        self,
        decision: ExecutionDecision,
        requested_quantity: float,
        reason: str,
    ) -> ExecutionPlan:
        return ExecutionPlan(
            exchange=decision.exchange,
            symbol=decision.symbol,
            action=decision.action,
            requested_quantity=requested_quantity,
            planned_quantity=0.0,
            remaining_quantity=requested_quantity,
            slice_count=0,
            slices=[],
            reason=reason,
            created_at=datetime.now(timezone.utc),
        )