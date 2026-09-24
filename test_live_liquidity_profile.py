import time

from src.analysis.live_liquidity import LiveLiquidityEngine
from src.exchanges.binance_orderbook_sync import BinanceOrderBookSync


engine = LiveLiquidityEngine(
    depth_levels=5,
)


updates = []


def on_order_book(order_book):
    state = engine.update(order_book)
    updates.append(state)


sync = BinanceOrderBookSync(
    symbol="BTC/USDT",
    snapshot_limit=100,
)


print("========== LIVE LIQUIDITY + PROFILE ==========")
print("Starting...")

sync.start(
    on_order_book=on_order_book,
)

print("\n========== INITIAL STATE ==========")
print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)

print("\n========== WAITING FOR LIVE DATA ==========")

time.sleep(10)

state = engine.latest_state

if state is None:
    sync.stop()
    raise RuntimeError(
        "No live liquidity state was received"
    )


print("\n========== BASIC LIQUIDITY ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)
print("Mid price:", state.mid_price)
print("Spread:", state.spread)
print("Spread %:", state.spread_percent)

print("Bid depth:", state.bid_depth_quantity)
print("Ask depth:", state.ask_depth_quantity)

print("Bid notional:", state.bid_depth_notional)
print("Ask notional:", state.ask_depth_notional)

print("\n========== DISTANCE PROFILE ==========")

for band in state.profile.bands:
    print(
        f"\n--- {band.distance_bps:g} bps ---"
    )

    print("Bid quantity:", band.bid_quantity)
    print("Ask quantity:", band.ask_quantity)

    print("Bid notional:", band.bid_notional)
    print("Ask notional:", band.ask_notional)

    print("Total notional:", band.total_notional)

    print("Bid ratio:", band.bid_ratio)
    print("Ask ratio:", band.ask_ratio)


print("\n========== ENGINE ==========")

print(
    "Liquidity updates:",
    engine.update_count,
)

print(
    "Callback updates:",
    len(updates),
)


print("\n========== ORDER BOOK SYNC ==========")

print(
    "Received events:",
    sync.received_events,
)

print(
    "Applied events:",
    sync.applied_events,
)

print(
    "Gaps:",
    sync.gap_count,
)

print(
    "Resyncs:",
    sync.resync_count,
)

print(
    "Errors:",
    sync.error_count,
)


sync.stop()

print("\n========== STOPPED ==========")

print("Running:", sync.is_running)
print("Synchronized:", sync.is_synchronized)

print("==============================================")
