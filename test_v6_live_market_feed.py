import time

from src.analysis.v6_live_market_feed import V6LiveMarketFeed

feed = V6LiveMarketFeed(
    symbol="BTC/USDT",
    snapshot_limit=1000,
)

feed.start()

try:
    time.sleep(5)

    book = feed.get_latest_order_book()

    print("V6 LIVE MARKET FEED")
    print()
    print("Running:", feed.is_running)
    print("Synchronized:", feed.is_synchronized)
    print("Updates:", feed.update_count)
    print("Received events:", feed.received_event_count)
    print("Applied events:", feed.applied_event_count)
    print("Gaps:", feed.gap_count)
    print("Resyncs:", feed.resync_count)
    print("Errors:", feed.error_count)
    print()
    print("Symbol:", book.symbol)
    print("Best bid:", book.best_bid.price)
    print("Best ask:", book.best_ask.price)
    print("Spread:", book.spread)
    print("Spread %:", book.spread_percent)
    print("Bids:", len(book.bids))
    print("Asks:", len(book.asks))
    print()
    print("VALIDATION")
    print("Feed running:", feed.is_running)
    print("Feed synchronized:", feed.is_synchronized)
    print("Received updates:", feed.update_count > 0)
    print("Valid best bid:", book.best_bid.price > 0)
    print("Valid best ask:", book.best_ask.price > book.best_bid.price)
    print("No gaps:", feed.gap_count == 0)
    print("No errors:", feed.error_count == 0)

finally:
    feed.stop()

print()
print("Stopped:", not feed.is_running)
