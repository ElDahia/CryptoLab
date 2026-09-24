from datetime import datetime, timezone

from src.analysis.live_microstructure import (
    LiveMicrostructureEngine,
)
from src.exchanges.models import (
    OrderBook,
    OrderBookLevel,
)


order_book = OrderBook(
    exchange="binance",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(83500.0, 1.5),
        OrderBookLevel(83499.0, 2.0),
        OrderBookLevel(83498.0, 3.0),
        OrderBookLevel(83497.0, 1.0),
        OrderBookLevel(83496.0, 2.5),
    ],
    asks=[
        OrderBookLevel(83501.0, 1.0),
        OrderBookLevel(83502.0, 2.5),
        OrderBookLevel(83503.0, 1.5),
        OrderBookLevel(83504.0, 3.0),
        OrderBookLevel(83505.0, 2.0),
    ],
    received_at=datetime.now(timezone.utc),
)


engine = LiveMicrostructureEngine(
    depth_levels=5,
    decay=1.0,
)


state = engine.update(order_book)


print("========== LIVE MICROSTRUCTURE TEST ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("\n========== MARKET STATE ==========")

print("Best bid:", state.best_bid)
print("Best ask:", state.best_ask)
print("Mid price:", state.mid_price)
print("Spread:", state.spread)
print("Spread %:", state.spread_percent)

print("\n========== ORDER BOOK PRESSURE ==========")

print("Imbalance:", state.imbalance)
print("Weighted imbalance:", state.weighted_imbalance)

print("\n========== ENGINE ==========")

print("Update count:", engine.update_count)
print("Has latest state:", engine.latest_state is not None)

print("\n==============================================")