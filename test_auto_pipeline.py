import time

from src.analysis.trade_stream import TradeStream
from src.exchanges.binance_ws import BinanceTradeWebSocket


stream = TradeStream()

ws = BinanceTradeWebSocket(
    symbol="BTC/USDT",
    trade_stream=stream,
)

ws.start()

time.sleep(5)

ws.stop()

stats = stream.stats()
state = stream.activity_state()

print()
print("========== CRYPTOLAB AUTO PIPELINE ==========")
print("WebSocket received:", ws.received_count)
print("WebSocket processed:", ws.processed_count)
print("WebSocket errors:", ws.error_count)
print("Stream received:", stats.received_count)
print("Stream emitted:", stats.emitted_count)
print("Duplicates:", stats.duplicate_count)
print("Rejected:", stats.rejected_count)
print("Stream errors:", stats.error_count)

if state:
    print("Activity trades:", state.trade_count)
    print("Buy volume:", state.buy_volume)
    print("Sell volume:", state.sell_volume)
    print("Net volume:", state.net_volume)
    print("CVD:", state.cvd)
    print("Trades/sec:", state.trades_per_second)
    print("Volume/sec:", state.volume_per_second)
    print("Notional/sec:", state.notional_per_second)
else:
    print("Activity state: None")

print("Stream running:", stream.is_running)
print("WebSocket running:", ws.is_running)
print("=============================================")
