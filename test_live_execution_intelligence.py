from datetime import datetime, timezone

from src.analysis.live_execution_intelligence import (
    LiveExecutionIntelligenceEngine,
)
from src.analysis.microstructure import MarketTrade
from src.exchanges.binance_orderbook_snapshot import (
    BinanceOrderBookSnapshot,
)

print("=" * 70)
print("CRYPTOLAB EXECUTION INTELLIGENCE TEST")
print("=" * 70)

snapshot_provider = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_provider.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print(f"Snapshot update ID: {update_id}")
print(f"Best bid: {order_book.best_bid.price}")
print(f"Best ask: {order_book.best_ask.price}")

engine = LiveExecutionIntelligenceEngine(
    symbol="BTC/USDT",
    buy_quantity=10.0,
    sell_quantity=10.0,
)

print()
print("Injecting test trade into order-flow engine...")

trade = MarketTrade(
    exchange="binance",
    symbol="BTC/USDT",
    price=order_book.best_ask.price,
    quantity=0.25,
    timestamp=datetime.now(timezone.utc),
    is_buyer_maker=False,
    trade_id="test-1",
)

engine.update_trade(trade)

print("Trade injected.")

print()
print("Building execution-intelligence state...")

state = engine.update_order_book(order_book)

print()
print("--- MARKET ---")
print(f"Mid price: {state.mid_price}")
print(f"Spread: {state.spread}")
print(f"Spread %: {state.spread_percent}")

print()
print("--- MICROSTRUCTURE ---")
print(f"Imbalance: {state.imbalance}")
print(f"Weighted imbalance: {state.weighted_imbalance}")

print()
print("--- ORDER FLOW ---")
print(f"Trade count: {state.trade_count}")
print(f"Buy volume: {state.buy_volume}")
print(f"Sell volume: {state.sell_volume}")
print(f"Net volume: {state.net_volume}")
print(f"CVD: {state.cvd}")

print()
print("--- LIQUIDITY ---")
print(f"Bid depth: {state.bid_depth_notional}")
print(f"Ask depth: {state.ask_depth_notional}")
print(f"Total depth: {state.total_depth_notional}")

print()
print("--- MARKET IMPACT ---")
print(f"BUY 10 BTC impact: {state.buy_price_impact_percent}%")
print(f"SELL 10 BTC impact: {state.sell_price_impact_percent}%")
print(f"BUY levels: {state.buy_levels_consumed}")
print(f"SELL levels: {state.sell_levels_consumed}")
print(f"BUY fully filled: {state.buy_fully_filled}")
print(f"SELL fully filled: {state.sell_fully_filled}")

print()
print("--- ENGINE ---")
print(f"Intelligence updates: {engine.update_count}")

print()
print("=" * 70)
print("TEST COMPLETE")
print("=" * 70)
