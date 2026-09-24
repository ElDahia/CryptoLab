from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.adaptive_execution_planner_v4 import AdaptiveExecutionPlannerV4
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.analysis.execution_planner import ExecutionPlan, ExecutionSlice
from src.analysis.execution_simulator import ExecutionSimulator


snapshot_client = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print("CRYPTOLAB V4 -> EXECUTION SIMULATOR INTEGRATION TEST")
print()
print("Snapshot update ID:", update_id)
print("Best bid:", order_book.best_bid.price)
print("Best ask:", order_book.best_ask.price)
print("Spread %:", order_book.spread_percent)
print()

planner = AdaptiveExecutionPlannerV4(
    max_slices=20,
    minimum_slice_quantity=0.01,
    liquidity_distance_bps=10.0,
    impact_search_iterations=18,
)

requested_quantity = 100.0

decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=order_book.received_at,
    action="BUY",
    reason="V4 integration test",
    confidence=0.90,
    buy_score=0.90,
    sell_score=0.10,
    market_impact_percent=0.05,
    spread_percent=0.02,
    imbalance=0.50,
    weighted_imbalance=0.50,
    net_volume=1.0,
    cvd=1.0,
    fully_filled=True,
)

risk = RiskAssessment(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=order_book.received_at,
    approved=True,
    action="BUY",
    requested_quantity=requested_quantity,
    allowed_quantity=requested_quantity,
    reason="V4 integration test",
    confidence=0.90,
    market_impact_percent=0.05,
    spread_percent=0.02,
    position_quantity=0.0,
    projected_position_quantity=requested_quantity,
    daily_pnl=0.0,
    risk_score=0.0,
)

v4_plan = planner.create_plan(
    order_book,
    decision,
    risk,
)

print("V4 PLAN")
print("Requested:", f"{v4_plan.requested_quantity:.6f}", "BTC")
print("Planned:", f"{v4_plan.planned_quantity:.6f}", "BTC")
print("Remaining:", f"{v4_plan.remaining_quantity:.6f}", "BTC")
print("Impact-limited:", f"{v4_plan.impact_limited_quantity:.6f}", "BTC")
print("Slices:", v4_plan.slice_count)
print()

simulator_slices = tuple(
    ExecutionSlice(
        sequence=item.sequence,
        action=item.action,
        quantity=item.quantity,
        max_impact_percent=item.max_impact_percent,
        max_spread_percent=item.max_spread_percent,
    )
    for item in v4_plan.slices
)

simulation_plan = ExecutionPlan(
    exchange=v4_plan.exchange,
    symbol=v4_plan.symbol,
    action=v4_plan.action,
    requested_quantity=v4_plan.planned_quantity,
    planned_quantity=v4_plan.planned_quantity,
    remaining_quantity=0.0,
    slice_count=v4_plan.slice_count,
    slices=simulator_slices,
    reason="V4 integration test",
    created_at=v4_plan.created_at,
)

simulator = ExecutionSimulator()

result = simulator.simulate(
    order_book=order_book,
    plan=simulation_plan,
)

print("EXECUTION SIMULATION")
print("Requested:", f"{result.requested_quantity:.6f}", "BTC")
print("Filled:", f"{result.filled_quantity:.6f}", "BTC")
print("Unfilled:", f"{result.unfilled_quantity:.6f}", "BTC")
print("Fill ratio:", f"{result.fill_ratio:.6%}")
print("Average execution:", f"{result.average_execution_price:.6f}")
print("Total notional:", f"{result.total_notional:.2f}")
print("Total slippage %:", f"{result.total_slippage_percent:.6f}%")
print("Total market impact %:", f"{result.total_market_impact_percent:.6f}%")
print("Fully filled:", result.fully_filled)
print("Executed slices:", result.slice_count)
print()

print("SLICE VALIDATION")

for fill in result.fills:
    print(
        f"#{fill.sequence:02d} "
        f"requested={fill.requested_quantity:.6f} | "
        f"filled={fill.filled_quantity:.6f} | "
        f"avg={fill.average_execution_price:.6f} | "
        f"impact={fill.market_impact_percent:.6f}%"
    )

print()
print("INTEGRATION CHECK")

print(
    "Planner planned == simulator requested:",
    abs(
        v4_plan.planned_quantity
        - result.requested_quantity
    ) < 1e-9,
)

print(
    "Planner planned == simulator filled:",
    abs(
        v4_plan.planned_quantity
        - result.filled_quantity
    ) < 1e-9,
)

print(
    "No double-counted liquidity:",
    result.filled_quantity <= v4_plan.planned_quantity + 1e-9,
)

print(
    "Simulation completed:",
    result.slice_count == v4_plan.slice_count,
)
