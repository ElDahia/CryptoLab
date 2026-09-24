from src.exchanges.binance_orderbook_snapshot import (
    BinanceOrderBookSnapshot,
)


provider = BinanceOrderBookSnapshot()

order_book, update_id = provider.get_snapshot(
    symbol="BTC/USDT",
    limit=100,
)

print("\n========== BINANCE SNAPSHOT ==========")
print("Exchange:", order_book.exchange)
print("Symbol:", order_book.symbol)
print("Snapshot update ID:", update_id)
print("Bids:", len(order_book.bids))
print("Asks:", len(order_book.asks))
print("Best bid:", order_book.best_bid.price)
print("Best bid quantity:", order_book.best_bid.quantity)
print("Best ask:", order_book.best_ask.price)
print("Best ask quantity:", order_book.best_ask.quantity)
print("Spread:", order_book.spread)
print("Spread %:", order_book.spread_percent)
print("======================================")
