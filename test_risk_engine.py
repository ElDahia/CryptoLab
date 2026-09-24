from datetime import datetime, timezone

from src.analysis.execution_decision import (
    ExecutionDecision,
)
from src.analysis.risk_engine import (
    RiskEngine,
)

print("=" * 70)
print("CRYPTOLAB RISK ENGINE TEST")
print("=" * 70)

risk = RiskEngine(
    max_order_quantity=10.0,
    max_position_quantity=20.0,
    max_market_impact_percent=0.05,
    max_spread_percent=0.02,
    minimum_confidence=0.60,
    daily_loss_limit=1000.0,
)

print()
print("--- SCENARIO 1: APPROVED ORDER ---")

approved_decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=datetime.now(timezone.utc),
    action="BUY",
    reason="test decision",
    confidence=0.85,
    buy_score=0.85,
    sell_score=0.20,
    market_impact_percent=0.01,
    spread_percent=0.005,
    imbalance=0.30,
    weighted_imbalance=0.35,
    net_volume=2.0,
    cvd=2.0,
    fully_filled=True,
)

assessment = risk.assess(
    decision=approved_decision,
    requested_quantity=5.0,
)

print(f"Approved: {assessment.approved}")
print(f"Action: {assessment.action}")
print(f"Requested: {assessment.requested_quantity}")
print(f"Allowed: {assessment.allowed_quantity}")
print(f"Blocked: {assessment.blocked_quantity}")
print(f"Reason: {assessment.reason}")
print(f"Risk score: {assessment.risk_score}")
print(f"Current position: {assessment.position_quantity}")
print(
    f"Projected position: "
    f"{assessment.projected_position_quantity}"
)

print()
print("--- SCENARIO 2: ORDER TOO LARGE ---")

large_order_assessment = risk.assess(
    decision=approved_decision,
    requested_quantity=25.0,
)

print(f"Approved: {large_order_assessment.approved}")
print(f"Action: {large_order_assessment.action}")
print(
    f"Requested: "
    f"{large_order_assessment.requested_quantity}"
)
print(
    f"Allowed: "
    f"{large_order_assessment.allowed_quantity}"
)
print(
    f"Blocked: "
    f"{large_order_assessment.blocked_quantity}"
)
print(
    f"Reason: "
    f"{large_order_assessment.reason}"
)
print(
    f"Risk score: "
    f"{large_order_assessment.risk_score}"
)

print()
print("--- SCENARIO 3: KILL SWITCH ---")

risk.enable_kill_switch()

kill_assessment = risk.assess(
    decision=approved_decision,
    requested_quantity=5.0,
)

print(f"Approved: {kill_assessment.approved}")
print(f"Action: {kill_assessment.action}")
print(f"Allowed: {kill_assessment.allowed_quantity}")
print(f"Reason: {kill_assessment.reason}")
print(f"Kill switch: {risk.kill_switch_enabled}")

print()
print("--- ENGINE ---")
print(f"Assessment count: {risk.assessment_count}")

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
