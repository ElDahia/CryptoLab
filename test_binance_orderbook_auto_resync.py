import time


from src.exchanges.binance_orderbook_sync import (
    BinanceOrderBookSync,
)


sync = BinanceOrderBookSync(
    symbol="BTC/USDT",
    snapshot_limit=100,
    max_resync_attempts=3,
    resync_retry_delay=0.25,
)


print("========== FORCED BUFFER GAP TEST ==========")

print("Starting Binance sync...")

sync.start()


print("\n========== INITIAL SYNC ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("Last update ID:", sync.last_update_id)
print("Received events:", sync.received_events)
print("Applied events:", sync.applied_events)
print("Gaps:", sync.gap_count)
print("Resyncs:", sync.resync_count)
print("Resync failures:", sync.resync_failure_count)
print("Errors:", sync.error_count)


if not sync.is_synchronized:
    raise RuntimeError(
        "Initial synchronization failed"
    )


print("\nWaiting for live processing...")
time.sleep(2)


with sync._lock:
    current_id = sync.last_update_id

    fake_gap_event = {
        "U": current_id + 100,
        "u": current_id + 101,
        "b": [],
        "a": [],
    }

    sync._events.appendleft(
        fake_gap_event
    )


print("\n========== GAP INJECTED ==========")
print("Current update ID:", current_id)
print(
    "Injected event:",
    current_id + 100,
    "->",
    current_id + 101,
)


print("\nWaiting for automatic resynchronization...")

time.sleep(5)


print("\n========== AFTER AUTOMATIC RESYNC ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("Last update ID:", sync.last_update_id)
print("Received events:", sync.received_events)
print("Applied events:", sync.applied_events)
print("Gaps:", sync.gap_count)
print("Resyncs:", sync.resync_count)
print("Resync failures:", sync.resync_failure_count)
print("Errors:", sync.error_count)


sync.stop()


print("\n========== FINAL ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("Gaps:", sync.gap_count)
print("Resyncs:", sync.resync_count)
print("Resync failures:", sync.resync_failure_count)
print("Errors:", sync.error_count)
print("================================")