from datetime import datetime, timezone

from src.exchanges.models import OrderBook, OrderBookLevel
from src.exchanges.order_book_reconstructor import (
    OrderBookReconstructor,
    OrderBookUpdate,
)


snapshot = OrderBook(
    exchange="binance",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(price=100.0, quantity=2.0),
        OrderBookLevel(price=99.0, quantity=3.0),
    ],
    asks=[
        OrderBookLevel(price=101.0, quantity=2.0),
        OrderBookLevel(price=102.0, quantity=4.0),
    ],
    received_at=datetime.now(timezone.utc),
)


reconstructor = OrderBookReconstructor(
    exchange="binance",
    symbol="BTC/USDT",
)


reconstructor.initialize_from_snapshot(
    order_book=snapshot,
    snapshot_update_id=100,
)


print("Initialized:", reconstructor.is_initialized)
print("Snapshot update ID:", reconstructor.last_update_id)


update_1 = OrderBookUpdate(
    first_update_id=101,
    final_update_id=101,
    bids=[
        OrderBookLevel(price=100.0, quantity=5.0),
    ],
    asks=[],
)

reconstructor.apply_update(update_1)

book = reconstructor.build_order_book()

print("\n--- AFTER UPDATE 1 ---")
print("Last update ID:", reconstructor.last_update_id)
print("Best bid:", book.best_bid.price, book.best_bid.quantity)
print("Best ask:", book.best_ask.price, book.best_ask.quantity)


update_2 = OrderBookUpdate(
    first_update_id=102,
    final_update_id=103,
    bids=[],
    asks=[
        OrderBookLevel(price=101.0, quantity=0.0),
        OrderBookLevel(price=100.5, quantity=1.5),
    ],
)

reconstructor.apply_update(update_2)

book = reconstructor.build_order_book()

print("\n--- AFTER UPDATE 2 ---")
print("Last update ID:", reconstructor.last_update_id)
print("Best bid:", book.best_bid.price, book.best_bid.quantity)
print("Best ask:", book.best_ask.price, book.best_ask.quantity)


gap_detected = False

try:
    gap_update = OrderBookUpdate(
        first_update_id=105,
        final_update_id=105,
        bids=[
            OrderBookLevel(price=98.0, quantity=1.0),
        ],
        asks=[],
    )

    reconstructor.apply_update(gap_update)

except RuntimeError as error:
    gap_detected = True
    print("\n--- GAP TEST ---")
    print("Gap detected:", error)


print("\n========== TEST RESULT ==========")
print("Initialized:", reconstructor.is_initialized)
print("Final update ID:", reconstructor.last_update_id)
print("Gap detection:", gap_detected)
print("Final bids:", len(reconstructor.build_order_book().bids))
print("Final asks:", len(reconstructor.build_order_book().asks))
print("=================================")
