from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskEngine
from src.analysis.adaptive_execution_engine_v5 import (
    AdaptiveExecutionEngineV5,
)


SYMBOL = "BTC/USDT"
REQUESTED_QUANTITY = 10.0


snapshot_client = BinanceOrderBookSnapshot()

order_book, snapshot_id = snapshot_client.get_snapshot(
    symbol=SYMBOL,
    limit=1000,
)

print("BINANCE LIVE DEPTH-AWARE EXECUTION V5.2")
print()
print("Snapshot ID:", snapshot_id)
print("Exchange:", order_book.exchange)
print("Symbol:", order_book.symbol)
print("Best bid:", order_book.best_bid.price)
print("Best ask:", order_book.best_ask.price)
print("Spread:", order_book.spread)
print("Spread %:", order_book.spread_percent)
print("Ask levels:", len(order_book.asks))
print("Bid levels:", len(order_book.bids))
print()


decision = ExecutionDecision(
    exchange=order_book.exchange,
    symbol=order_book.symbol,
    timestamp=order_book.received_at,
    action="BUY",
    reason="Live Binance V5.2 depth-aware simulation",
    confidence=1.0,
    buy_score=1.0,
    sell_score=0.0,
    market_impact_percent=0.0,
    spread_percent=order_book.spread_percent,
    imbalance=0.0,
    weighted_imbalance=0.0,
    net_volume=0.0,
    cvd=0.0,
    fully_filled=True,
)


risk_engine = RiskEngine(
    max_order_quantity=REQUESTED_QUANTITY,
    max_position_quantity=20.0,
    max_market_impact_percent=0.05,
    max_spread_percent=0.02,
    minimum_confidence=0.60,
    daily_loss_limit=1000.0,
)


risk = risk_engine.assess(
    decision=decision,
    requested_quantity=REQUESTED_QUANTITY,
)


print("RISK")
print("Approved:", risk.approved)
print("Allowed quantity:", risk.allowed_quantity)
print("Reason:", risk.reason)
print()


engine = AdaptiveExecutionEngineV5(
    max_slices=20,
    minimum_slice_quantity=0.01,
    max_impact_percent=0.05,
    max_spread_percent=0.02,
    impact_search_iterations=18,
    max_slice_fraction_of_liquidity=0.25,
    max_levels_per_slice=20,
)


result = engine.simulate(
    order_book=order_book,
    decision=decision,
    risk_assessment=risk,
)


print("EXECUTION RESULT")
print("Requested:", result.requested_quantity)
print("Planned:", result.planned_quantity)
print("Filled:", result.filled_quantity)
print("Unfilled:", result.unfilled_quantity)
print("Fill ratio:", result.fill_ratio)
print("Average execution:", result.average_execution_price)
print("Total notional:", result.total_notional)
print("Slippage %:", result.total_slippage_percent)
print("Market impact %:", result.total_market_impact_percent)
print("Fully filled:", result.fully_filled)
print("Slices:", result.slice_count)
print()


for execution_slice in result.slices:
    print(
        f"Slice #{execution_slice.sequence}: "
        f"qty={execution_slice.quantity:.6f} | "
        f"avg={execution_slice.average_execution_price:.6f} | "
        f"impact={execution_slice.market_impact_percent:.6f}% | "
        f"slippage={execution_slice.slippage_percent:.6f}% | "
        f"levels={execution_slice.levels_consumed} | "
        f"remaining={execution_slice.remaining_quantity:.6f} | "
        f"liquidity={execution_slice.remaining_liquidity:.6f}"
    )


print()
print("VALIDATION")
print(
    "Correct requested quantity:",
    result.requested_quantity == REQUESTED_QUANTITY,
)
print(
    "No overfill:",
    result.filled_quantity
    <= result.planned_quantity + 1e-9,
)
print(
    "Risk respected:",
    result.planned_quantity
    <= risk.allowed_quantity + 1e-9,
)
print(
    "Execution completed:",
    result.fully_filled,
)
print(
    "Adaptive slicing:",
    result.slice_count > 1,
)
print(
    "Depth limit respected:",
    all(
        execution_slice.levels_consumed <= 20
        for execution_slice in result.slices
    ),
)
print(
    "Remaining quantity decreases:",
    all(
        result.slices[i].remaining_quantity
        < result.slices[i - 1].remaining_quantity
        for i in range(1, len(result.slices))
    ),
)
print(
    "Remaining liquidity decreases:",
    all(
        result.slices[i].remaining_liquidity
        < result.slices[i - 1].remaining_liquidity
        for i in range(1, len(result.slices))
    ),
)
