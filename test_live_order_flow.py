import time

from src.analysis.live_order_flow import (
    LiveOrderFlowEngine,
)
from src.exchanges.binance_ws import (
    BinanceTradeWebSocket,
)


engine = LiveOrderFlowEngine(
    exchange="binance",
    symbol="BTC/USDT",
)


updates = []


def on_trade(trade):
    state = engine.update(trade)
    updates.append(state)


stream = BinanceTradeWebSocket(
    symbol="BTC/USDT",
)


print("========== LIVE ORDER FLOW TEST ==========")

print("Starting...")

stream.start(
    on_trade=on_trade,
)


print("\n========== WAITING FOR LIVE TRADES ==========")

time.sleep(10)


state = engine.latest_state


if state is None:
    stream.stop()
    raise RuntimeError(
        "No live order-flow state was received"
    )


print("\n========== ORDER FLOW ==========")

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("Trade count:", state.trade_count)

print("Buy volume:", state.buy_volume)
print("Sell volume:", state.sell_volume)

print("Buy notional:", state.buy_notional)
print("Sell notional:", state.sell_notional)

print("Net volume:", state.net_volume)
print("Net notional:", state.net_notional)

print("Buy ratio:", state.buy_ratio)
print("Sell ratio:", state.sell_ratio)

print("\n========== CVD ==========")

print("CVD:", state.cvd)

print("\n========== STREAM ==========")

print("Received trades:", stream.received_count)
print("Errors:", stream.error_count)

print("\n========== CALLBACK ==========")

print("Order-flow updates:", len(updates))


stream.stop()


print("\n========== STOPPED ==========")

print("Running:", stream.is_running)

print("==========================================")