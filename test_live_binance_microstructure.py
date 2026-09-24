import time

from src.exchanges.binance_orderbook_sync import (
    BinanceOrderBookSync,
)


sync = BinanceOrderBookSync(
    symbol="BTC/USDT",
    snapshot_limit=100,
    microstructure_depth_levels=5,
    microstructure_decay=1.0,
)


microstructure_updates = []


def on_microstructure(state):
    microstructure_updates.append(state)


print("========== LIVE BINANCE MICROSTRUCTURE ==========")

print("Starting...")

sync.start(
    on_microstructure=on_microstructure,
)

print("\n========== INITIAL STATE ==========")

print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)
print("Last update ID:", sync.last_update_id)

print("\n========== WAITING FOR LIVE DATA ==========")

time.sleep(5)


state = sync.get_microstructure()


print("\n========== LIVE MICROSTRUCTURE ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("Best bid:", state.best_bid)
print("Best ask:", state.best_ask)
print("Mid price:", state.mid_price)
print("Spread:", state.spread)
print("Spread %:", state.spread_percent)

print("\n========== ORDER BOOK PRESSURE ==========")

print("Imbalance:", state.imbalance)
print("Weighted imbalance:", state.weighted_imbalance)

print("\n========== ENGINE ==========")

print(
    "Microstructure updates:",
    sync.microstructure_update_count,
)

print(
    "Callback updates:",
    len(microstructure_updates),
)

print("\n========== SYNC ENGINE ==========")

print("Received events:", sync.received_events)
print("Applied events:", sync.applied_events)
print("Gaps:", sync.gap_count)
print("Resyncs:", sync.resync_count)
print("Resync failures:", sync.resync_failure_count)
print("Errors:", sync.error_count)


sync.stop()


print("\n========== STOPPED ==========")

print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)

print("==============================================")