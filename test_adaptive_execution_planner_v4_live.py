from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.adaptive_execution_planner_v4 import AdaptiveExecutionPlannerV4
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment


snapshot_client = BinanceOrderBookSnapshot()
order_book, update_id = snapshot_client.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print("ADAPTIVE EXECUTION PLANNER V4 - LIVE BINANCE TEST")
print()
print("Snapshot update ID:", update_id)
print("Best bid:", order_book.best_bid.price)
print("Best ask:", order_book.best_ask.price)
print("Spread:", order_book.spread)
print("Spread %:", order_book.spread_percent)
print("Bids:", len(order_book.bids))
print("Asks:", len(order_book.asks))
print()

planner = AdaptiveExecutionPlannerV4(
    max_slices=20,
    minimum_slice_quantity=0.01,
    liquidity_distance_bps=10.0,
    impact_search_iterations=18,
)


for requested_quantity in (5.0, 100.0, 500.0):
    decision = ExecutionDecision(
        exchange="binance",
        symbol="BTC/USDT",
        timestamp=order_book.received_at,
        action="BUY",
        reason="live V4 research test",
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
        reason="live V4 research test",
        confidence=0.90,
        market_impact_percent=0.05,
        spread_percent=0.02,
        position_quantity=0.0,
        projected_position_quantity=requested_quantity,
        daily_pnl=0.0,
        risk_score=0.0,
    )

    plan = planner.create_plan(
        order_book,
        decision,
        risk,
    )

    print("=" * 70)
    print(f"SCENARIO: {requested_quantity:.2f} BTC")
    print()
    print("Risk approved:", risk.approved)
    print("Requested:", f"{plan.requested_quantity:.6f}", "BTC")
    print("Planned:", f"{plan.planned_quantity:.6f}", "BTC")
    print("Remaining:", f"{plan.remaining_quantity:.6f}", "BTC")
    print(
        "Available liquidity:",
        f"{plan.available_liquidity:.6f}",
        "BTC",
    )
    print(
        "Impact-limited quantity:",
        f"{plan.impact_limited_quantity:.6f}",
        "BTC",
    )
    print(
        "Max impact:",
        f"{plan.max_impact_percent:.6f}%",
    )
    print("Slice count:", plan.slice_count)
    print("Reason:", plan.reason)
    print()

    for item in plan.slices:
        print(
            f"#{item.sequence:02d} "
            f"qty={item.quantity:.6f} BTC | "
            f"distance={item.price_distance_bps:.4f} bps | "
            f"source={item.source_liquidity:.6f} BTC | "
            f"utilization={item.utilization:.2%} | "
            f"impact={item.estimated_impact_percent:.6f}% | "
            f"slippage={item.estimated_slippage_percent:.6f}%"
        )

    print()
