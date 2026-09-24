import time

from src.analysis.live_liquidity import (
    LiveLiquidityEngine,
)
from src.exchanges.binance_orderbook_sync import (
    BinanceOrderBookSync,
)


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


print("========== LIVE LIQUIDITY ENGINE ==========")

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


print("\n========== LIVE LIQUIDITY ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("Mid price:", state.mid_price)
print("Spread:", state.spread)
print("Spread %:", state.spread_percent)


print("\n========== DEPTH ==========")

print(
    "Bid depth quantity:",
    state.bid_depth_quantity,
)

print(
    "Ask depth quantity:",
    state.ask_depth_quantity,
)

print(
    "Bid depth notional:",
    state.bid_depth_notional,
)

print(
    "Ask depth notional:",
    state.ask_depth_notional,
)

print(
    "Total depth quantity:",
    state.total_depth_quantity,
)

print(
    "Total depth notional:",
    state.total_depth_notional,
)


print("\n========== LIQUIDITY DISTRIBUTION ==========")

print(
    "Bid liquidity ratio:",
    state.bid_liquidity_ratio,
)

print(
    "Ask liquidity ratio:",
    state.ask_liquidity_ratio,
)

print(
    "Bid notional ratio:",
    state.bid_notional_ratio,
)

print(
    "Ask notional ratio:",
    state.ask_notional_ratio,
)


print("\n========== CONCENTRATION ==========")

print(
    "Bid concentration:",
    state.bid_concentration,
)

print(
    "Ask concentration:",
    state.ask_concentration,
)


print("\n========== ENGINE ==========")

print(
    "Liquidity updates:",
    engine.update_count,
)

print(
    "Callback updates:",
    len(updates),
)


print("\n========== SYNC ENGINE ==========")

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

print("==========================================")
