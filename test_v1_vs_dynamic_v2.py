from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.execution_planner import ExecutionPlanner
from src.analysis.execution_simulator import ExecutionSimulator
from src.analysis.dynamic_execution_simulator_v2 import DynamicExecutionSimulatorV2


snapshot_client = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print("LIVE BINANCE SNAPSHOT")
print("Update ID:", update_id)
print("Best bid:", order_book.best_bid.price)
print("Best ask:", order_book.best_ask.price)
print("Spread:", order_book.spread)
print("Bids:", len(order_book.bids))
print("Asks:", len(order_book.asks))
print()

planner = ExecutionPlanner(
    default_slice_quantity=5.0,
    max_slices=20,
)

# Build a normal execution plan directly.
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from datetime import datetime, timezone

now = datetime.now(timezone.utc)

decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=now,
    action="BUY",
    reason="simulation comparison",
    confidence=1.0,
    buy_score=1.0,
    sell_score=0.0,
    market_impact_percent=0.0,
    spread_percent=0.0,
    imbalance=0.0,
    weighted_imbalance=0.0,
    net_volume=0.0,
    cvd=0.0,
    fully_filled=True,
)

risk = RiskAssessment(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=now,
    approved=True,
    action="BUY",
    requested_quantity=100.0,
    allowed_quantity=100.0,
    reason="simulation comparison",
    confidence=1.0,
    market_impact_percent=0.0,
    spread_percent=0.0,
    position_quantity=0.0,
    projected_position_quantity=100.0,
    daily_pnl=0.0,
    risk_score=0.0,
)

plan = planner.create_plan(
    decision=decision,
    risk_assessment=risk,
)

print("EXECUTION PLAN")
print("Requested:", plan.requested_quantity)
print("Planned:", plan.planned_quantity)
print("Slices:", plan.slice_count)
print()

v1 = ExecutionSimulator()

v1_result = v1.simulate(
    order_book=order_book,
    plan=plan,
)

v2 = DynamicExecutionSimulatorV2()

v2_result = v2.simulate(
    order_book=order_book,
    plan=plan,
)

print("=" * 60)
print("V1 — STATIC SEQUENTIAL SIMULATOR")
print("=" * 60)
print("Requested:", v1_result.requested_quantity)
print("Filled:", v1_result.filled_quantity)
print("Unfilled:", v1_result.unfilled_quantity)
print("Fill ratio:", v1_result.fill_ratio)
print("Average execution:", v1_result.average_execution_price)
print("Total notional:", v1_result.total_notional)
print("Slippage %:", v1_result.total_slippage_percent)
print("Market impact %:", v1_result.total_market_impact_percent)
print("Executed slices:", v1_result.slice_count)
print()

print("=" * 60)
print("V2 — DYNAMIC SEQUENTIAL BOOK")
print("=" * 60)
print("Requested:", v2_result.requested_quantity)
print("Filled:", v2_result.filled_quantity)
print("Unfilled:", v2_result.unfilled_quantity)
print("Fill ratio:", v2_result.fill_ratio)
print("Average execution:", v2_result.average_execution_price)
print("Total notional:", v2_result.total_notional)
print("Slippage %:", v2_result.total_slippage_percent)
print("Market impact %:", v2_result.total_market_impact_percent)
print("Executed slices:", v2_result.slice_count)
print()

print("=" * 60)
print("COMPARISON")
print("=" * 60)
print(
    "Filled difference:",
    v1_result.filled_quantity - v2_result.filled_quantity,
)
print(
    "Average execution difference:",
    v1_result.average_execution_price
    - v2_result.average_execution_price,
)
print(
    "Notional difference:",
    v1_result.total_notional
    - v2_result.total_notional,
)
print(
    "V2 fully filled:",
    v2_result.fully_filled,
)
print(
    "V2 completed:",
    v2_result.is_complete,
)
