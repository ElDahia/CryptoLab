import time

from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.analysis.v6_market_state import V6MarketStateMonitor


feed = V6LiveMarketFeed(
    symbol="BTC/USDT",
    snapshot_limit=1000,
)

monitor = V6MarketStateMonitor()

feed.start()

try:
    deadline = time.monotonic() + 5.0

    while (
        not feed.is_synchronized
        or feed.latest_order_book is None
    ):
        if time.monotonic() >= deadline:
            raise TimeoutError(
                "Timed out waiting for synchronized live order book"
            )

        time.sleep(0.01)

    print("V6.1 LIVE MARKET STATE MONITOR")
    print()

    previous_update = 0

    states = []

    while len(states) < 10:
        if feed.update_count > previous_update:
            book = feed.get_latest_order_book()

            state = monitor.update(book)

            states.append(state)

            previous_update = feed.update_count

            print(
                f"Update #{state.update_number}: "
                f"mid={state.mid_price:.2f} | "
                f"spread={state.spread:.6f} | "
                f"spread%={state.spread_percent:.8f}% | "
                f"bid_depth={state.bid_depth_quantity:.6f} | "
                f"ask_depth={state.ask_depth_quantity:.6f} | "
                f"mid_change={state.mid_price_change:.6f} | "
                f"liquidity_change={state.liquidity_change:.6f}"
            )

        time.sleep(0.01)

    print()
    print("VALIDATION")

    print(
        "Received 10 states:",
        len(states) == 10,
    )

    print(
        "Update numbers increasing:",
        all(
            states[i].update_number
            > states[i - 1].update_number
            for i in range(1, len(states))
        ),
    )

    print(
        "Valid bid/ask:",
        all(
            state.best_ask > state.best_bid
            for state in states
        ),
    )

    print(
        "Positive mid prices:",
        all(
            state.mid_price > 0
            for state in states
        ),
    )

    print(
        "Non-negative depth:",
        all(
            state.bid_depth_quantity >= 0
            and state.ask_depth_quantity >= 0
            for state in states
        ),
    )

    print(
        "Monitor has latest state:",
        monitor.latest_state is not None,
    )

    print()
    print("FEED")
    print("Updates:", feed.update_count)
    print("Received events:", feed.received_event_count)
    print("Applied events:", feed.applied_event_count)
    print("Gaps:", feed.gap_count)
    print("Resyncs:", feed.resync_count)
    print("Errors:", feed.error_count)

finally:
    feed.stop()

print()
print("Feed stopped:", not feed.is_running)
