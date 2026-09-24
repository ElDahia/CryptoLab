import time

from src.analysis.trade_stream import TradeStream
from src.exchanges.binance_ws import BinanceTradeWebSocket
from src.exchanges.okx_ws import OKXTradeWebSocket
from src.exchanges.stream_manager import ExchangeStreamManager


binance_stream = TradeStream()
okx_stream = TradeStream()

binance = BinanceTradeWebSocket(
    symbol="BTC/USDT",
    trade_stream=binance_stream,
)

okx = OKXTradeWebSocket(
    symbol="BTC/USDT",
    trade_stream=okx_stream,
)

manager = ExchangeStreamManager(
    streams=[
        binance,
        okx,
    ],
)

print("Registered exchanges:", manager.exchanges)
print("Stream count:", manager.stream_count)

manager.start_all()

time.sleep(5)

running_stats = manager.stats()

print()
print("========== MULTI-EXCHANGE LIVE ==========")
print("Running streams:", running_stats.running_count)
print("Total received:", running_stats.received_count)
print("Total processed:", running_stats.processed_count)
print("Total errors:", running_stats.error_count)

print()
print("---------- BINANCE ----------")
print("Received:", binance.received_count)
print("Processed:", binance.processed_count)
print("Errors:", binance.error_count)

binance_state = binance_stream.activity_state()

if binance_state:
    print("Trades:", binance_state.trade_count)
    print("Net volume:", binance_state.net_volume)
    print("CVD:", binance_state.cvd)

print()
print("------------ OKX ------------")
print("Received:", okx.received_count)
print("Processed:", okx.processed_count)
print("Errors:", okx.error_count)

okx_state = okx_stream.activity_state()

if okx_state:
    print("Trades:", okx_state.trade_count)
    print("Net volume:", okx_state.net_volume)
    print("CVD:", okx_state.cvd)

manager.stop_all()

time.sleep(0.5)

stopped_stats = manager.stats()

print()
print("========== AFTER STOP ==========")
print("Running streams:", stopped_stats.running_count)
print("Manager running:", stopped_stats.is_running)
print("Binance running:", binance.is_running)
print("OKX running:", okx.is_running)
print("================================")
