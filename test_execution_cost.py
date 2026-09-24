from src.analysis.execution_cost import ExecutionCostEngine
from src.analysis.execution_simulator import ExecutionSimulationResult
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskEngine
from src.analysis.execution_planner import ExecutionPlanner


snapshot_client = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print("LIVE BINANCE")
print(f"Snapshot update ID: {update_id}")
print(f"Best bid: {order_book.best_bid.price}")
print(f"Best ask: {order_book.best_ask.price}")
print(f"Spread: {order_book.spread}")
print()


decision = ExecutionDecision(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=order_book.received_at,
    action="BUY",
    reason="execution cost test",
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


cost_engine = ExecutionCostEngine()


for requested_quantity in [5.0, 100.0, 500.0]:

    print("=" * 70)
    print(f"SCENARIO: {requested_quantity} BTC")
    print("=" * 70)

    risk_engine = RiskEngine(
        max_order_quantity=requested_quantity,
        max_position_quantity=requested_quantity * 2,
    )

    risk = risk_engine.assess(
        decision,
        requested_quantity,
    )

    planner = ExecutionPlanner(
        default_slice_quantity=1.0,
        max_slices=20,
    )

    plan = planner.create_plan(
        decision,
        risk,
    )

    from src.analysis.execution_simulator import ExecutionSimulator

    simulator = ExecutionSimulator()

    simulation = simulator.simulate(
        order_book,
        plan,
    )

    cost = cost_engine.calculate(
        simulation,
    )

    print(f"Requested quantity:          {cost.requested_quantity:.6f} BTC")
    print(f"Filled quantity:             {cost.filled_quantity:.6f} BTC")
    print(f"Unfilled quantity:           {cost.unfilled_quantity:.6f} BTC")
    print(f"Fill ratio:                  {cost.fill_ratio:.6f}")
    print()
    print(f"Reference price:             {cost.reference_price:.6f}")
    print(f"Average execution price:     {cost.average_execution_price:.6f}")
    print(f"Gross notional:               ${cost.gross_notional:,.2f}")
    print()
    print(f"Trading fee:                 ${cost.trading_fee:,.6f}")
    print(f"Slippage cost:               ${cost.slippage_cost:,.6f}")
    print(f"Market impact cost:          ${cost.market_impact_cost:,.6f}")
    print(f"TOTAL EXECUTION COST:        ${cost.total_execution_cost:,.6f}")
    print(f"TOTAL COST %:                {cost.total_execution_cost_percent:.8f}%")
    print()
    print(f"Implementation shortfall:    ${cost.implementation_shortfall:,.6f}")
    print(f"Shortfall %:                 {cost.implementation_shortfall_percent:.8f}%")
    print(f"Fully filled:                {cost.fully_filled}")
    print()
