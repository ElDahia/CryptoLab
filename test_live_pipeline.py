import time

from src.analysis.trade_stream import TradeStream
from src.exchanges.binance_ws import BinanceTradeWebSocket


stream = TradeStream(
    interval_seconds=1.0,
)

received = []


def on_trade(trade):
    received.append(trade)


ws = BinanceTradeWebSocket("BTC/USDT")


def handle_trade(trade):
    stream.process_trade(
        trade,
        on_trade=on_trade,
    )


stream.start()
ws.start(handle_trade)

time.sleep(5)

ws.stop()
stream.stop()

state = stream.activity_state()
stats = stream.stats()

print()
print("========== CRYPTOLAB LIVE PIPELINE ==========")
print("WebSocket trades:", ws.received_count)
print("WebSocket errors:", ws.error_count)
print("Stream received:", stats.received_count)
print("Stream emitted:", stats.emitted_count)
print("Duplicates:", stats.duplicate_count)
print("Rejected:", stats.rejected_count)
print("Errors:", stats.error_count)
print("Activity trades:", state.trade_count if state else 0)

if state:
    print("Buy volume:", state.buy_volume)
    print("Sell volume:", state.sell_volume)
    print("Net volume:", state.net_volume)
    print("CVD:", state.cvd)
    print("Trades/sec:", state.trades_per_second)
    print("Volume/sec:", state.volume_per_second)
    print("Notional/sec:", state.notional_per_second)

print("Stream running:", stream.is_running)
print("WebSocket running:", ws.is_running)
print("==============================================")
