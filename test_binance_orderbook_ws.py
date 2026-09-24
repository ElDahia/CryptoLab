import time

from src.exchanges.binance_orderbook_ws import BinanceOrderBookWebSocket


received = []

def on_order_book(order_book):
    received.append(order_book)

    if len(received) <= 3:
        print("\n--- ORDER BOOK UPDATE ---")
        print("Exchange:", order_book.exchange)
        print("Symbol:", order_book.symbol)
        print("Bids:", len(order_book.bids))
        print("Asks:", len(order_book.asks))
        print("Best bid:", order_book.best_bid.price)
        print("Best ask:", order_book.best_ask.price)
        print("Spread:", order_book.spread)


ws = BinanceOrderBookWebSocket("BTC/USDT")

ws.start(on_order_book=on_order_book)

time.sleep(5)

ws.stop()

print("\n========== TEST RESULT ==========")
print("Received updates:", ws.received_count)
print("Errors:", ws.error_count)
print("Running:", ws.is_running)
print("Last update ID:", ws.last_update_id)

if received:
    latest = received[-1]
    print("Latest bids:", len(latest.bids))
    print("Latest asks:", len(latest.asks))
    print("Latest best bid:", latest.best_bid.price)
    print("Latest best ask:", latest.best_ask.price)
    print("Latest spread:", latest.spread)
else:
    print("No order book updates received.")

print("=================================")
