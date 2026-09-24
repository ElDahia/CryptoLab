import time

from src.exchanges.binance_ws import BinanceTradeWebSocket


trades = []


def on_trade(trade):
    trades.append(trade)

    print(
        "Trade:",
        len(trades),
        trade.trade_id,
    )


ws = BinanceTradeWebSocket("BTC/USDT")

ws.start(on_trade)

time.sleep(5)

ws.stop()

print()
print("Received:", len(trades))
print("WebSocket count:", ws.received_count)
print("Errors:", ws.error_count)
print("Running:", ws.is_running)
