import time

from src.analysis.trade_stream import TradeStream
from src.exchanges.binance_ws import BinanceTradeWebSocket
from src.exchanges.stream_manager import ExchangeStreamManager


stream = TradeStream()

binance = BinanceTradeWebSocket(
    symbol="BTC/USDT",
    trade_stream=stream,
)

manager = ExchangeStreamManager(
    streams=[binance],
)

print("Registered exchanges:", manager.exchanges)
print("Stream count:", manager.stream_count)

manager.start_all()

time.sleep(5)

stats_running = manager.stats()

print()
print("========== STREAM MANAGER RUNNING ==========")
print("Running streams:", stats_running.running_count)
print("Received:", stats_running.received_count)
print("Processed:", stats_running.processed_count)
print("Errors:", stats_running.error_count)
print("Manager running:", stats_running.is_running)

manager.stop_all()

time.sleep(0.5)

stats_stopped = manager.stats()

print()
print("========== STREAM MANAGER STOPPED ==========")
print("Running streams:", stats_stopped.running_count)
print("Received:", stats_stopped.received_count)
print("Processed:", stats_stopped.processed_count)
print("Errors:", stats_stopped.error_count)
print("Manager running:", stats_stopped.is_running)
print("Binance running:", binance.is_running)
print("============================================")
