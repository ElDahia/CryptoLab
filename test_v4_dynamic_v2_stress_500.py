from datetime import datetime, timezone

from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.analysis.adaptive_execution_planner_v4 import AdaptiveExecutionPlannerV4
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
print("Spread %:", order_book.spread_percent)
print("Bids:", len(order_book.bids))
print("Asks:", len(order_book.asks))
print()

now = datetime.now(timezone.utc)

requested_quantity = 500.0

decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=now,
    action="BUY",
    reason="500 BTC V4 stress test",
    confidence=1.0,
    buy_score=1.0,
    sell_score=0.0,
    market_impact_percent=0.05,
    spread_percent=0.02,
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
    requested_quantity=requested_quantity,
    allowed_quantity=requested_quantity,
    reason="500 BTC V4 stress test",
    confidence=1.0,
    market_impact_percent=0.05,
    spread_percent=0.02,
    position_quantity=0.0,
    projected_position_quantity=requested_quantity,
    daily_pnl=0.0,
    risk_score=0.0,
)

planner = AdaptiveExecutionPlannerV4(
    max_slices=20,
    minimum_slice_quantity=0.01,
    liquidity_distance_bps=10.0,
    impact_search_iterations=18,
)

plan = planner.create_plan(
    order_book=order_book,
    decision=decision,
    risk_assessment=risk,
)

print("=" * 60)
print("V4 STRESS PLAN — 500 BTC")
print("=" * 60)
print("Requested:", plan.requested_quantity)
print("Planned:", plan.planned_quantity)
print("Remaining:", plan.remaining_quantity)
print("Available liquidity:", plan.available_liquidity)
print("Impact-limited quantity:", plan.impact_limited_quantity)
print("Max impact:", plan.max_impact_percent)
print("Slices:", plan.slice_count)
print()

simulator = DynamicExecutionSimulatorV2()

result = simulator.simulate(
    order_book=order_book,
    plan=plan,
)

print("=" * 60)
print("DYNAMIC SIMULATOR V2 — 500 BTC")
print("=" * 60)
print("Requested:", result.requested_quantity)
print("Filled:", result.filled_quantity)
print("Unfilled:", result.unfilled_quantity)
print("Fill ratio:", result.fill_ratio)
print("Average execution:", result.average_execution_price)
print("Total notional:", result.total_notional)
print("Total slippage:", result.total_slippage)
print("Total slippage %:", result.total_slippage_percent)
print("Total market impact:", result.total_market_impact)
print("Total market impact %:", result.total_market_impact_percent)
print("Fully filled:", result.fully_filled)
print("Executed slices:", result.slice_count)
print()

print("=" * 60)
print("STRESS VALIDATION")
print("=" * 60)
print(
    "Planner limited quantity:",
    plan.planned_quantity < requested_quantity,
)

print(
    "Simulator filled <= planner planned:",
    result.filled_quantity
    <= plan.planned_quantity + 1e-9,
)

print(
    "Unfilled quantity preserved:",
    result.unfilled_quantity
    >= 0.0,
)

print(
    "No overfill:",
    result.filled_quantity
    <= result.requested_quantity + 1e-9,
)
