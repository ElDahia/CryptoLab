import time

from src.analysis.live_market_runtime import (
    LiveMarketRuntime,
)


runtime = LiveMarketRuntime(
    symbol="BTC/USDT",
    snapshot_limit=100,
    microstructure_depth_levels=5,
    microstructure_decay=1.0,
)


states = []


def on_market_state(state):
    states.append(state)


print("========== LIVE MARKET RUNTIME ==========")

print("Starting...")

runtime.start(
    on_market_state=on_market_state,
)


print("\n========== INITIAL STATE ==========")

print("Running:", runtime.is_running)
print("Synchronized:", runtime.is_synchronized)

print("\n========== WAITING FOR LIVE MARKET ==========")

time.sleep(10)


state = runtime.get_state()


print("\n========== LIVE MARKET STATE ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("\n--- MARKET ---")

print("Best bid:", state.best_bid)
print("Best ask:", state.best_ask)
print("Mid price:", state.mid_price)
print("Spread:", state.spread)
print("Spread %:", state.spread_percent)

print("\n--- ORDER BOOK ---")

print("Imbalance:", state.imbalance)
print("Weighted imbalance:", state.weighted_imbalance)

print("\n--- ORDER FLOW ---")

print("Trade count:", state.trade_count)
print("Buy volume:", state.buy_volume)
print("Sell volume:", state.sell_volume)
print("Net volume:", state.net_volume)
print("Net notional:", state.net_notional)
print("Buy ratio:", state.buy_ratio)
print("Sell ratio:", state.sell_ratio)
print("CVD:", state.cvd)

print("\n========== RUNTIME STATS ==========")

print("Market state updates:", runtime.market_state_update_count)
print("Order book updates:", runtime.order_book_update_count)
print("Received trades:", runtime.received_trade_count)
print("Processed trades:", runtime.trade_count)
print("Trade errors:", runtime.trade_error_count)
print("Order book received events:", runtime.order_book_received_events)
print("Order book applied events:", runtime.order_book_applied_events)
print("Order book gaps:", runtime.order_book_gap_count)
print("Order book resyncs:", runtime.order_book_resync_count)
print("Order book errors:", runtime.order_book_error_count)

print("\n========== CALLBACK ==========")

print("Combined state callbacks:", len(states))


runtime.stop()


print("\n========== STOPPED ==========")

print("Running:", runtime.is_running)
print("Synchronized:", runtime.is_synchronized)

print("==========================================")
