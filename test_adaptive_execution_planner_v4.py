from datetime import datetime, timezone

from src.analysis.adaptive_execution_planner_v4 import AdaptiveExecutionPlannerV4
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.exchanges.models import OrderBook, OrderBookLevel


book = OrderBook(
    exchange="test",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(100.0, 10.0),
        OrderBookLevel(99.0, 10.0),
    ],
    asks=[
        OrderBookLevel(101.0, 1.0),
        OrderBookLevel(102.0, 1.0),
        OrderBookLevel(110.0, 20.0),
    ],
    received_at=datetime.now(timezone.utc),
)

decision = ExecutionDecision(
    exchange="test",
    symbol="BTC/USDT",
    timestamp=datetime.now(timezone.utc),
    action="BUY",
    reason="test",
    confidence=0.90,
    buy_score=0.90,
    sell_score=0.10,
    market_impact_percent=0.05,
    spread_percent=1.0,
    imbalance=0.5,
    weighted_imbalance=0.5,
    net_volume=1.0,
    cvd=1.0,
    fully_filled=True,
)

risk = RiskAssessment(
    exchange="test",
    symbol="BTC/USDT",
    timestamp=datetime.now(timezone.utc),
    approved=True,
    action="BUY",
    requested_quantity=5.0,
    allowed_quantity=5.0,
    reason="test",
    confidence=0.90,
    market_impact_percent=5.0,
    spread_percent=2.0,
    position_quantity=0.0,
    projected_position_quantity=5.0,
    daily_pnl=0.0,
    risk_score=0.0,
)

planner = AdaptiveExecutionPlannerV4(
    max_slices=5,
    minimum_slice_quantity=0.01,
    liquidity_distance_bps=1000.0,
)

plan = planner.create_plan(book, decision, risk)

print("ACTION:", plan.action)
print("REQUESTED:", plan.requested_quantity)
print("PLANNED:", plan.planned_quantity)
print("REMAINING:", plan.remaining_quantity)
print("IMPACT LIMITED:", plan.impact_limited_quantity)
print("SLICES:", plan.slice_count)
print("REASON:", plan.reason)

for item in plan.slices:
    print(
        f"SLICE {item.sequence}: "
        f"qty={item.quantity:.6f} "
        f"impact={item.estimated_impact_percent:.6f}% "
        f"utilization={item.utilization:.2%}"
    )
