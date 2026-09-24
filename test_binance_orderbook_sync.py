import json
import threading
import time
from datetime import datetime, timezone

import requests
import websocket

from src.exchanges.models import OrderBook, OrderBookLevel
from src.exchanges.order_book_reconstructor import (
    OrderBookReconstructor,
    OrderBookUpdate,
)


SYMBOL = "BTC/USDT"
EXCHANGE_SYMBOL = SYMBOL.replace("/", "").lower()

WS_URL = (
    "wss://stream.binance.com:9443/ws/"
    f"{EXCHANGE_SYMBOL}@depth@100ms"
)

events = []
lock = threading.Lock()
connected = threading.Event()


def on_open(ws):
    connected.set()
    print("WebSocket connected")


def on_message(ws, message):
    data = json.loads(message)

    if "U" not in data or "u" not in data:
        return

    with lock:
        events.append(data)


def on_error(ws, error):
    print("WebSocket error:", error)


def on_close(ws, code, message):
    print("WebSocket closed")


socket = websocket.WebSocketApp(
    WS_URL,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close,
)


thread = threading.Thread(
    target=socket.run_forever,
    daemon=True,
)

thread.start()


if not connected.wait(timeout=5):
    raise RuntimeError(
        "WebSocket did not connect within 5 seconds"
    )


time.sleep(0.5)


response = requests.get(
    "https://api.binance.com/api/v3/depth",
    params={
        "symbol": SYMBOL.replace("/", ""),
        "limit": 100,
    },
    timeout=10,
)

response.raise_for_status()

snapshot_data = response.json()

snapshot_update_id = int(
    snapshot_data["lastUpdateId"]
)

snapshot = OrderBook(
    exchange="binance",
    symbol=SYMBOL,
    bids=[
        OrderBookLevel(
            price=float(price),
            quantity=float(quantity),
        )
        for price, quantity in snapshot_data["bids"]
        if float(quantity) > 0
    ],
    asks=[
        OrderBookLevel(
            price=float(price),
            quantity=float(quantity),
        )
        for price, quantity in snapshot_data["asks"]
        if float(quantity) > 0
    ],
    received_at=datetime.now(timezone.utc),
)


print("\n========== SNAPSHOT ==========")
print("Snapshot update ID:", snapshot_update_id)
print("Snapshot bids:", len(snapshot.bids))
print("Snapshot asks:", len(snapshot.asks))
print("==============================")


time.sleep(1)


with lock:
    buffered_events = list(events)


print("\nBuffered events:", len(buffered_events))


reconstructor = OrderBookReconstructor(
    exchange="binance",
    symbol=SYMBOL,
)


reconstructor.initialize_from_snapshot(
    order_book=snapshot,
    snapshot_update_id=snapshot_update_id,
)


selected_event = None


for event in buffered_events:

    first_update_id = int(event["U"])
    final_update_id = int(event["u"])

    if final_update_id <= snapshot_update_id:
        continue

    if (
        first_update_id
        <= snapshot_update_id + 1
        <= final_update_id
    ):
        selected_event = event
        break


if selected_event is None:
    print(
        "\nNo bridging WebSocket event found."
    )

    print(
        "This can happen because the snapshot and"
        " WebSocket timing window was too wide."
    )

    socket.close()

    raise SystemExit(0)


first_update_id = int(
    selected_event["U"]
)

final_update_id = int(
    selected_event["u"]
)


print("\n========== BRIDGING EVENT ==========")
print(
    "Event:",
    first_update_id,
    "->",
    final_update_id,
)
print(
    "Required point:",
    snapshot_update_id + 1,
)
print("====================================")


update = OrderBookUpdate(
    first_update_id=first_update_id,
    final_update_id=final_update_id,
    bids=[
        OrderBookLevel(
            price=float(price),
            quantity=float(quantity),
        )
        for price, quantity in selected_event["b"]
    ],
    asks=[
        OrderBookLevel(
            price=float(price),
            quantity=float(quantity),
        )
        for price, quantity in selected_event["a"]
    ],
)


reconstructor.apply_update(update)


applied_count = 1


for event in buffered_events:

    if event is selected_event:
        continue

    first_update_id = int(event["U"])
    final_update_id = int(event["u"])

    if final_update_id <= reconstructor.last_update_id:
        continue

    update = OrderBookUpdate(
        first_update_id=first_update_id,
        final_update_id=final_update_id,
        bids=[
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in event["b"]
        ],
        asks=[
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in event["a"]
        ],
    )

    try:
        reconstructor.apply_update(update)
        applied_count += 1

    except RuntimeError as error:
        print(
            "\nSequence error:",
            error,
        )
        break


socket.close()


final_book = reconstructor.build_order_book()


print("\n========== SYNC RESULT ==========")
print("Applied updates:", applied_count)
print("Final update ID:", reconstructor.last_update_id)
print("Final bids:", len(final_book.bids))
print("Final asks:", len(final_book.asks))
print("Best bid:", final_book.best_bid.price)
print("Best ask:", final_book.best_ask.price)
print("Spread:", final_book.spread)
print("=================================")
