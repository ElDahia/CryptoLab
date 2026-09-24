import time

from src.exchanges.binance_orderbook_sync import (
    BinanceOrderBookSync,
)


sync = BinanceOrderBookSync(
    symbol="BTC/USDT",
    snapshot_limit=100,
)


updates = []


def on_order_book(order_book):
    updates.append(order_book)


print("Starting synchronization...")

sync.start(
    on_order_book=on_order_book,
)

print("\n========== SYNCED ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("Received events:", sync.received_events)
print("Applied events:", sync.applied_events)
print("Skipped events:", sync.skipped_events)
print("Gaps:", sync.gap_count)
print("Errors:", sync.error_count)
print("Last update ID:", sync.last_update_id)


time.sleep(3)


book = sync.get_order_book()

print("\n========== LIVE BOOK ==========")
print("Updates received by callback:", len(updates))
print("Bids:", len(book.bids))
print("Asks:", len(book.asks))
print("Best bid:", book.best_bid.price)
print("Best ask:", book.best_ask.price)
print("Spread:", book.spread)
print("Spread %:", book.spread_percent)
print("================================")


sync.stop()

print("\n========== STOPPED ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("================================")
