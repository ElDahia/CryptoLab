import time

from src.exchanges.okx_ws import OKXTradeWebSocket


trades = []


def on_trade(trade):
    trades.append(trade)

    print(
        "Trade:",
        len(trades),
        trade.trade_id,
        trade.price,
        trade.quantity,
        trade.is_buyer_maker,
    )


ws = OKXTradeWebSocket("BTC/USDT")

ws.start(on_trade)

time.sleep(5)

ws.stop()

print()
print("========== OKX WEBSOCKET TEST ==========")
print("Received:", ws.received_count)
print("Errors:", ws.error_count)
print("Running:", ws.is_running)

if trades:
    print("First exchange:", trades[0].exchange)
    print("First symbol:", trades[0].symbol)
    print("First trade ID:", trades[0].trade_id)

print("========================================")
