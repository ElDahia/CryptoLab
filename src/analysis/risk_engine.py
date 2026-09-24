from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_decision import (
    ExecutionDecision,
)


@dataclass(frozen=True)
class RiskAssessment:
    """
    Result of a pre-execution risk assessment.

    This component does not place or modify real orders.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    approved: bool

    action: str
    requested_quantity: float
    allowed_quantity: float

    reason: str

    confidence: float
    market_impact_percent: float
    spread_percent: float

    position_quantity: float
    projected_position_quantity: float

    daily_pnl: float

    risk_score: float

    @property
    def blocked_quantity(self) -> float:
        return max(
            self.requested_quantity
            - self.allowed_quantity,
            0.0,
        )

    @property
    def is_actionable(self) -> bool:
        return (
            self.approved
            and self.action in {"BUY", "SELL"}
            and self.allowed_quantity > 0
        )

    def age_seconds(self) -> float:
        return (
            datetime.now(timezone.utc)
            - self.timestamp
        ).total_seconds()

    def is_fresh(
        self,
        max_age_seconds: float = 5.0,
    ) -> bool:
        return self.age_seconds() <= max_age_seconds


class RiskEngine:
    """
    Pre-execution risk-control engine.

    Evaluates an ExecutionDecision against configurable
    position, order-size, execution-cost, confidence,
    and daily-loss limits.

    This engine does not place real orders.
    """

    def __init__(
        self,
        max_order_quantity: float = 10.0,
        max_position_quantity: float = 20.0,
        max_market_impact_percent: float = 0.05,
        max_spread_percent: float = 0.02,
        minimum_confidence: float = 0.60,
        daily_loss_limit: float = 1000.0,
    ):
        if max_order_quantity <= 0:
            raise ValueError(
                "max_order_quantity must be greater than zero"
            )

        if max_position_quantity <= 0:
            raise ValueError(
                "max_position_quantity must be greater than zero"
            )

        if max_market_impact_percent <= 0:
            raise ValueError(
                "max_market_impact_percent must be greater than zero"
            )

        if max_spread_percent <= 0:
            raise ValueError(
                "max_spread_percent must be greater than zero"
            )

        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        if daily_loss_limit <= 0:
            raise ValueError(
                "daily_loss_limit must be greater than zero"
            )

        self.max_order_quantity = max_order_quantity
        self.max_position_quantity = (
            max_position_quantity
        )
        self.max_market_impact_percent = (
            max_market_impact_percent
        )
        self.max_spread_percent = (
            max_spread_percent
        )
        self.minimum_confidence = minimum_confidence
        self.daily_loss_limit = daily_loss_limit

        self._position_quantity = 0.0
        self._daily_pnl = 0.0

        self._kill_switch = False

        self._latest_assessment: (
            RiskAssessment | None
        ) = None

        self._assessment_count = 0

    @property
    def latest_assessment(
        self,
    ) -> RiskAssessment | None:
        return self._latest_assessment

    @property
    def assessment_count(self) -> int:
        return self._assessment_count

    @property
    def position_quantity(self) -> float:
        return self._position_quantity

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl

    @property
    def kill_switch_enabled(self) -> bool:
        return self._kill_switch

    def set_position(
        self,
        quantity: float,
    ) -> None:
        self._position_quantity = quantity

    def set_daily_pnl(
        self,
        pnl: float,
    ) -> None:
        self._daily_pnl = pnl

    def enable_kill_switch(self) -> None:
        self._kill_switch = True

    def disable_kill_switch(self) -> None:
        self._kill_switch = False

    def assess(
        self,
        decision: ExecutionDecision,
        requested_quantity: float,
    ) -> RiskAssessment:
        """
        Assess whether an execution decision is allowed.
        """

        if requested_quantity <= 0:
            raise ValueError(
                "requested_quantity must be greater than zero"
            )

        action = decision.action

        reasons = []

        allowed_quantity = requested_quantity
        approved = True

        if action not in {"BUY", "SELL"}:
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "decision is not actionable"
            )

        if self._kill_switch:
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "kill switch is enabled"
            )

        if decision.confidence < self.minimum_confidence:
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "confidence is below risk threshold"
            )

        if (
            decision.market_impact_percent
            > self.max_market_impact_percent
        ):
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "market impact exceeds risk limit"
            )

        if (
            decision.spread_percent
            > self.max_spread_percent
        ):
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "spread exceeds risk limit"
            )

        if (
            self._daily_pnl
            <= -self.daily_loss_limit
        ):
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "daily loss limit reached"
            )

        if requested_quantity > self.max_order_quantity:
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "requested order exceeds maximum order size"
            )

        if action == "BUY":
            projected_position = (
                self._position_quantity
                + allowed_quantity
            )

        elif action == "SELL":
            projected_position = (
                self._position_quantity
                - allowed_quantity
            )

        else:
            projected_position = (
                self._position_quantity
            )

        if (
            abs(projected_position)
            > self.max_position_quantity
        ):
            approved = False
            allowed_quantity = 0.0
            reasons.append(
                "projected position exceeds position limit"
            )

        if not reasons:
            reasons.append(
                "risk checks passed"
            )

        risk_score = 0.0

        if decision.confidence < self.minimum_confidence:
            risk_score += 0.25

        if (
            decision.market_impact_percent
            > self.max_market_impact_percent
        ):
            risk_score += 0.25

        if (
            decision.spread_percent
            > self.max_spread_percent
        ):
            risk_score += 0.20

        if (
            requested_quantity
            > self.max_order_quantity
        ):
            risk_score += 0.15

        if (
            abs(projected_position)
            > self.max_position_quantity
        ):
            risk_score += 0.15

        risk_score = min(
            risk_score,
            1.0,
        )

        assessment = RiskAssessment(
            exchange=decision.exchange,
            symbol=decision.symbol,
            timestamp=decision.timestamp,
            approved=approved,
            action=action,
            requested_quantity=requested_quantity,
            allowed_quantity=allowed_quantity,
            reason="; ".join(reasons),
            confidence=decision.confidence,
            market_impact_percent=(
                decision.market_impact_percent
            ),
            spread_percent=decision.spread_percent,
            position_quantity=self._position_quantity,
            projected_position_quantity=(
                self._position_quantity
                + (
                    allowed_quantity
                    if action == "BUY"
                    else -allowed_quantity
                    if action == "SELL"
                    else 0.0
                )
            ),
            daily_pnl=self._daily_pnl,
            risk_score=risk_score,
        )

        self._latest_assessment = assessment
        self._assessment_count += 1

        return assessment

    def apply_position_change(
        self,
        action: str,
        quantity: float,
    ) -> None:
        """
        Update the tracked position after a simulated
        execution/fill.

        This method does not communicate with an exchange.
        """

        normalized_action = action.upper().strip()

        if normalized_action not in {
            "BUY",
            "SELL",
        }:
            raise ValueError(
                "action must be 'BUY' or 'SELL'"
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be greater than zero"
            )

        if normalized_action == "BUY":
            self._position_quantity += quantity
        else:
            self._position_quantity -= quantity

    def reset(self) -> None:
        """
        Reset tracked risk state.
        """

        self._position_quantity = 0.0
        self._daily_pnl = 0.0
        self._kill_switch = False
        self._latest_assessment = None
        self._assessment_count = 0