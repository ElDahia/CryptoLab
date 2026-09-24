from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.live_execution_intelligence import (
    LiveExecutionIntelligenceState,
)


@dataclass(frozen=True)
class ExecutionDecision:
    """
    Structured execution decision produced from
    live execution-intelligence data.

    This component only produces a decision.
    It does not place real orders.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    action: str
    reason: str

    confidence: float

    buy_score: float
    sell_score: float

    market_impact_percent: float
    spread_percent: float

    imbalance: float
    weighted_imbalance: float

    net_volume: float
    cvd: float

    fully_filled: bool

    @property
    def is_actionable(self) -> bool:
        return self.action in {
            "BUY",
            "SELL",
        }

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


class ExecutionDecisionEngine:
    """
    Converts execution-intelligence state into a
    deterministic research decision.

    The current model is intentionally conservative
    and rule-based.

    It does not place real orders.
    """

    def __init__(
        self,
        minimum_confidence: float = 0.60,
        maximum_impact_percent: float = 0.05,
        maximum_spread_percent: float = 0.02,
    ):
        if not 0.0 <= minimum_confidence <= 1.0:
            raise ValueError(
                "minimum_confidence must be between 0 and 1"
            )

        if maximum_impact_percent <= 0:
            raise ValueError(
                "maximum_impact_percent must be greater than zero"
            )

        if maximum_spread_percent <= 0:
            raise ValueError(
                "maximum_spread_percent must be greater than zero"
            )

        self.minimum_confidence = minimum_confidence
        self.maximum_impact_percent = (
            maximum_impact_percent
        )
        self.maximum_spread_percent = (
            maximum_spread_percent
        )

        self._latest_decision: (
            ExecutionDecision | None
        ) = None

        self._decision_count = 0

    @property
    def latest_decision(
        self,
    ) -> ExecutionDecision | None:
        return self._latest_decision

    @property
    def decision_count(self) -> int:
        return self._decision_count

    def evaluate(
        self,
        state: LiveExecutionIntelligenceState,
    ) -> ExecutionDecision:
        """
        Evaluate the current market state.

        The scoring model combines:

        - order-book imbalance
        - weighted imbalance
        - executed trade-flow delta
        - CVD direction
        - execution cost
        - spread conditions

        The result is a research decision only.
        """

        buy_score = 0.0
        sell_score = 0.0

        reasons = []

        if state.imbalance > 0:
            buy_score += 0.25
        elif state.imbalance < 0:
            sell_score += 0.25

        if state.weighted_imbalance > 0:
            buy_score += 0.25
        elif state.weighted_imbalance < 0:
            sell_score += 0.25

        if state.net_volume > 0:
            buy_score += 0.20
        elif state.net_volume < 0:
            sell_score += 0.20

        if state.cvd > 0:
            buy_score += 0.20
        elif state.cvd < 0:
            sell_score += 0.20

        buy_impact = (
            state.buy_price_impact_percent
        )

        sell_impact = (
            state.sell_price_impact_percent
        )

        if buy_impact <= self.maximum_impact_percent:
            buy_score += 0.05

        if sell_impact <= self.maximum_impact_percent:
            sell_score += 0.05

        if state.spread_percent <= self.maximum_spread_percent:
            buy_score += 0.025
            sell_score += 0.025

        if buy_score > sell_score:
            action = "BUY"
            confidence = buy_score
            market_impact = buy_impact
            fully_filled = state.buy_fully_filled

            if state.imbalance > 0:
                reasons.append(
                    "positive order-book imbalance"
                )

            if state.weighted_imbalance > 0:
                reasons.append(
                    "positive weighted imbalance"
                )

            if state.net_volume > 0:
                reasons.append(
                    "positive net trade volume"
                )

            if state.cvd > 0:
                reasons.append(
                    "positive CVD"
                )

        elif sell_score > buy_score:
            action = "SELL"
            confidence = sell_score
            market_impact = sell_impact
            fully_filled = state.sell_fully_filled

            if state.imbalance < 0:
                reasons.append(
                    "negative order-book imbalance"
                )

            if state.weighted_imbalance < 0:
                reasons.append(
                    "negative weighted imbalance"
                )

            if state.net_volume < 0:
                reasons.append(
                    "negative net trade volume"
                )

            if state.cvd < 0:
                reasons.append(
                    "negative CVD"
                )

        else:
            action = "HOLD"
            confidence = 0.0
            market_impact = min(
                buy_impact,
                sell_impact,
            )
            fully_filled = (
                state.buy_fully_filled
                and state.sell_fully_filled
            )

            reasons.append(
                "buy and sell scores are equal"
            )

        if market_impact > self.maximum_impact_percent:
            reasons.append(
                "execution impact exceeds configured limit"
            )

        if state.spread_percent > self.maximum_spread_percent:
            reasons.append(
                "spread exceeds configured limit"
            )

        if action != "HOLD":
            if confidence < self.minimum_confidence:
                reasons.append(
                    "confidence below configured threshold"
                )
                action = "HOLD"

            elif market_impact > self.maximum_impact_percent:
                action = "HOLD"

            elif state.spread_percent > self.maximum_spread_percent:
                action = "HOLD"

        reason = "; ".join(reasons)

        decision = ExecutionDecision(
            exchange=state.exchange,
            symbol=state.symbol,
            timestamp=state.timestamp,
            action=action,
            reason=reason,
            confidence=confidence,
            buy_score=buy_score,
            sell_score=sell_score,
            market_impact_percent=market_impact,
            spread_percent=state.spread_percent,
            imbalance=state.imbalance,
            weighted_imbalance=state.weighted_imbalance,
            net_volume=state.net_volume,
            cvd=state.cvd,
            fully_filled=fully_filled,
        )

        self._latest_decision = decision
        self._decision_count += 1

        return decision

    def reset(self) -> None:
        """
        Clear the latest decision.
        """

        self._latest_decision = None
        self._decision_count = 0