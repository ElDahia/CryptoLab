from datetime import datetime, timezone

from src.analysis.execution_decision import (
    ExecutionDecisionEngine,
)
from src.analysis.live_execution_intelligence import (
    LiveExecutionIntelligenceEngine,
)
from src.analysis.microstructure import MarketTrade
from src.exchanges.binance_orderbook_snapshot import (
    BinanceOrderBookSnapshot,
)

print("=" * 70)
print("CRYPTOLAB EXECUTION DECISION TEST")
print("=" * 70)

snapshot_provider = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_provider.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print(f"Snapshot update ID: {update_id}")
print(f"Best bid: {order_book.best_bid.price}")
print(f"Best ask: {order_book.best_ask.price}")

intelligence = LiveExecutionIntelligenceEngine(
    symbol="BTC/USDT",
    buy_quantity=10.0,
    sell_quantity=10.0,
)

trade = MarketTrade(
    exchange="binance",
    symbol="BTC/USDT",
    price=order_book.best_ask.price,
    quantity=0.25,
    timestamp=datetime.now(timezone.utc),
    is_buyer_maker=False,
    trade_id="decision-test-1",
)

intelligence.update_trade(trade)

state = intelligence.update_order_book(
    order_book
)

decision_engine = ExecutionDecisionEngine(
    minimum_confidence=0.60,
    maximum_impact_percent=0.05,
    maximum_spread_percent=0.02,
)

decision = decision_engine.evaluate(state)

print()
print("--- DECISION ---")
print(f"Action: {decision.action}")
print(f"Reason: {decision.reason}")
print(f"Confidence: {decision.confidence}")
print(f"Buy score: {decision.buy_score}")
print(f"Sell score: {decision.sell_score}")

print()
print("--- MARKET CONDITIONS ---")
print(f"Spread %: {decision.spread_percent}")
print(f"Imbalance: {decision.imbalance}")
print(f"Weighted imbalance: {decision.weighted_imbalance}")
print(f"Net volume: {decision.net_volume}")
print(f"CVD: {decision.cvd}")

print()
print("--- EXECUTION COST ---")
print(
    f"Selected impact: "
    f"{decision.market_impact_percent}%"
)
print(
    f"Fully filled: "
    f"{decision.fully_filled}"
)

print()
print("--- ENGINE ---")
print(
    f"Decision count: "
    f"{decision_engine.decision_count}"
)

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
