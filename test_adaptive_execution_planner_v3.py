from src.analysis.adaptive_execution_planner_v3 import AdaptiveExecutionPlannerV3
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskEngine
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot


print("ADAPTIVE EXECUTION PLANNER V2 TEST")
print("=" * 75)

snapshot_client = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

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
    reason="adaptive planner v2 test",
    confidence=0.95,
    buy_score=0.95,
    sell_score=0.0,
    market_impact_percent=0.05,
    spread_percent=0.02,
    imbalance=0.5,
    weighted_imbalance=0.5,
    net_volume=1.0,
    cvd=1.0,
    fully_filled=True,
)


planner = AdaptiveExecutionPlannerV3(
    liquidity_utilization=0.10,
    max_slices=20,
    liquidity_distance_bps=10.0,
    minimum_slice_quantity=0.01,
)


for requested_quantity in [5.0, 100.0, 500.0]:

    print("=" * 75)
    print(f"SCENARIO: {requested_quantity} BTC")
    print("=" * 75)

    risk_engine = RiskEngine(
        max_order_quantity=requested_quantity,
        max_position_quantity=requested_quantity * 2,
    )

    risk = risk_engine.assess(
        decision,
        requested_quantity,
    )

    print(f"Risk approved:          {risk.approved}")
    print(f"Allowed quantity:       {risk.allowed_quantity:.6f}")
    print()

    plan = planner.create_plan(
        order_book=order_book,
        decision=decision,
        risk_assessment=risk,
    )

    print(f"Requested:              {plan.requested_quantity:.6f} BTC")
    print(f"Planned:                {plan.planned_quantity:.6f} BTC")
    print(f"Remaining:              {plan.remaining_quantity:.6f} BTC")
    print(f"Available liquidity:    {plan.available_liquidity:.6f} BTC")
    print(f"Capacity:               {plan.capacity_quantity:.6f} BTC")
    print(f"Utilization:            {plan.utilization_percent:.4f}%")
    print(f"Slice count:             {plan.slice_count}")
    print(f"Reason:                 {plan.reason}")
    print()

    if plan.slices:

        print("ADAPTIVE CHILD SLICES")
        print("-" * 75)

        for execution_slice in plan.slices:

            print(
                f"#{execution_slice.sequence:02d} "
                f"{execution_slice.action:<4} "
                f"{execution_slice.quantity:.6f} BTC "
                f"| Source liquidity: "
                f"{execution_slice.source_liquidity:.6f} BTC "
                f"| Used: "
                f"{execution_slice.liquidity_utilization_percent:.2f}%"
            )

    print()
