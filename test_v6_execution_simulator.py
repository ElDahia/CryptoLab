import time

from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.analysis.v6_execution_simulator import V6ExecutionSimulator


feed = V6LiveMarketFeed(
    symbol="BTC/USDT",
    snapshot_limit=1000,
)

feed.start()

try:
    print("STARTING V6 LIVE EXECUTION SIMULATION")
    print()

    deadline = time.monotonic() + 5.0

    while (
        not feed.is_synchronized
        and time.monotonic() < deadline
    ):
        time.sleep(0.01)

    if not feed.is_synchronized:
        raise RuntimeError(
            "V6 feed failed to synchronize"
        )

    print("Feed synchronized:", feed.is_synchronized)
    print("Initial updates:", feed.update_count)
    print()

    simulator = V6ExecutionSimulator(
        feed=feed,
        slice_quantity=0.5,
        update_timeout_seconds=5.0,
    )

    result = simulator.simulate(
        requested_quantity=2.0,
        action="BUY",
    )

    print("V6 EXECUTION RESULT")
    print()
    print("Requested:", result.requested_quantity)
    print("Filled:", result.filled_quantity)
    print("Unfilled:", result.unfilled_quantity)
    print("Fill ratio:", result.fill_ratio)
    print("Average execution:", result.average_execution_price)
    print("Total notional:", result.total_notional)
    print("Slippage %:", result.slippage_percent)
    print("Market impact %:", result.market_impact_percent)
    print("Fully filled:", result.fully_filled)
    print("Slices:", len(result.slices))
    print()

    for execution_slice in result.slices:
        print(
            f"Slice #{execution_slice.sequence}: "
            f"requested={execution_slice.requested_quantity:.6f} | "
            f"filled={execution_slice.filled_quantity:.6f} | "
            f"avg={execution_slice.average_execution_price:.6f} | "
            f"levels={execution_slice.levels_consumed} | "
            f"feed_update={execution_slice.feed_update_number}"
        )

    print()
    print("FEED STATE")
    print("Updates:", feed.update_count)
    print("Received events:", feed.received_event_count)
    print("Applied events:", feed.applied_event_count)
    print("Gaps:", feed.gap_count)
    print("Resyncs:", feed.resync_count)
    print("Errors:", feed.error_count)

    print()
    print("VALIDATION")

    print(
        "Correct requested quantity:",
        result.requested_quantity == 2.0,
    )

    print(
        "Correct slice count:",
        len(result.slices) == 4,
    )

    print(
        "Each slice is 0.5 BTC:",
        all(
            abs(
                execution_slice.requested_quantity - 0.5
            ) < 1e-9
            for execution_slice in result.slices
        ),
    )

    print(
        "Fully filled:",
        result.fully_filled,
    )

    print(
        "No overfill:",
        result.filled_quantity
        <= result.requested_quantity + 1e-9,
    )

    print(
        "Feed remained synchronized:",
        feed.is_synchronized,
    )

    print(
        "No gaps:",
        feed.gap_count == 0,
    )

    print(
        "No errors:",
        feed.error_count == 0,
    )

    print(
        "Fresh update between slices:",
        all(
            result.slices[i].feed_update_number
            > result.slices[i - 1].feed_update_number
            for i in range(1, len(result.slices))
        ),
    )

finally:
    feed.stop()

print()
print("Feed stopped:", not feed.is_running)
