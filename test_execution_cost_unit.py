from src.analysis.execution_cost import ExecutionCostEngine
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.execution_planner import ExecutionPlanner
from src.analysis.execution_simulator import ExecutionSimulator
from src.analysis.risk_engine import RiskEngine
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot


print("EXECUTION COST INTEGRATION TEST")
print("=" * 70)

snapshot_client = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=100,
)

print(f"Snapshot update ID: {update_id}")
print(f"Best bid: {order_book.best_bid.price}")
print(f"Best ask: {order_book.best_ask.price}")
print()

decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=order_book.received_at,
    action="BUY",
    reason="execution cost integration test",
    confidence=0.95,
    buy_score=0.95,
    sell_score=0.0,
    market_impact_percent=0.01,
    spread_percent=0.001,
    imbalance=0.5,
    weighted_imbalance=0.5,
    net_volume=1.0,
    cvd=1.0,
    fully_filled=True,
)

requested_quantity = 5.0

risk_engine = RiskEngine(
    max_order_quantity=requested_quantity,
    max_position_quantity=requested_quantity * 2,
)

risk = risk_engine.assess(
    decision,
    requested_quantity,
)

assert risk.approved is True

planner = ExecutionPlanner(
    default_slice_quantity=1.0,
    max_slices=20,
)

plan = planner.create_plan(
    decision,
    risk,
)

assert plan.is_actionable is True

simulator = ExecutionSimulator()

simulation = simulator.simulate(
    order_book,
    plan,
)

cost_engine = ExecutionCostEngine()

result = cost_engine.calculate(
    simulation,
)

print("SIMULATION")
print("-" * 70)
print(f"Requested:          {simulation.requested_quantity:.6f} BTC")
print(f"Filled:             {simulation.filled_quantity:.6f} BTC")
print(f"Unfilled:           {simulation.unfilled_quantity:.6f} BTC")
print(f"Average execution:  {simulation.average_execution_price:.6f}")
print(f"Total notional:     ${simulation.total_notional:,.2f}")
print()

print("EXECUTION COST")
print("-" * 70)
print(f"Trading fee:        ${result.trading_fee:,.6f}")
print(f"Price shortfall:    ${result.price_shortfall:,.6f}")
print(f"Impact cost:        ${result.market_impact_cost:,.6f}")
print(f"TOTAL COST:         ${result.total_execution_cost:,.6f}")
print(f"TOTAL COST %:       {result.total_execution_cost_percent:.8f}%")
print()

print("IMPLEMENTATION SHORTFALL")
print("-" * 70)
print(f"Shortfall:          ${result.implementation_shortfall:,.6f}")
print(f"Shortfall %:        {result.implementation_shortfall_percent:.8f}%")
print()

assert result.total_execution_cost >= result.trading_fee
assert result.total_execution_cost >= result.price_shortfall
assert result.total_execution_cost >= result.market_impact_cost

assert abs(
    result.total_execution_cost
    - (
        result.trading_fee
        + result.price_shortfall
        + result.market_impact_cost
    )
) < 1e-9

assert abs(
    result.price_shortfall
    - result.implementation_shortfall
) < 1e-9

print("PASS: real simulator integration")
print("PASS: fee included once")
print("PASS: price shortfall included once")
print("PASS: market impact included once")
print("PASS: no double counting")
print()
print("EXECUTION COST INTEGRATION TEST: SUCCESS")
