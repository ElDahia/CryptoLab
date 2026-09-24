from dataclasses import dataclass

from src.exchanges.models import OrderBook, OrderBookLevel


@dataclass(frozen=True)
class OrderBookUpdate:
    """
    Normalized order book delta update.

    first_update_id:
        First update ID contained in this event.

    final_update_id:
        Final update ID contained in this event.
    """

    first_update_id: int
    final_update_id: int

    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]


class OrderBookReconstructor:
    """
    Reconstruct a local order book from a REST snapshot
    followed by incremental WebSocket updates.

    The reconstructor is intentionally exchange-agnostic.
    Exchange-specific sequence rules are handled by the
    caller/adapter layer.
    """

    def __init__(
        self,
        exchange: str,
        symbol: str,
    ):
        self.exchange = exchange
        self.symbol = symbol

        self._bids: dict[float, float] = {}
        self._asks: dict[float, float] = {}

        self._last_update_id: int | None = None
        self._initialized = False

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    @property
    def last_update_id(self) -> int | None:
        return self._last_update_id

    def initialize_from_snapshot(
        self,
        order_book: OrderBook,
        snapshot_update_id: int,
    ) -> None:
        if order_book.exchange != self.exchange:
            raise ValueError(
                "snapshot exchange does not match reconstructor"
            )

        if order_book.symbol != self.symbol:
            raise ValueError(
                "snapshot symbol does not match reconstructor"
            )

        if snapshot_update_id < 0:
            raise ValueError(
                "snapshot_update_id must not be negative"
            )

        self._bids = {
            level.price: level.quantity
            for level in order_book.bids
            if level.quantity > 0
        }

        self._asks = {
            level.price: level.quantity
            for level in order_book.asks
            if level.quantity > 0
        }

        self._last_update_id = snapshot_update_id
        self._initialized = True

    def apply_update(
        self,
        update: OrderBookUpdate,
    ) -> None:
        if not self._initialized:
            raise RuntimeError(
                "order book reconstructor is not initialized"
            )

        if update.final_update_id <= self._last_update_id:
            return

        if update.first_update_id > self._last_update_id + 1:
            raise RuntimeError(
                "order book update gap detected"
            )

        for level in update.bids:
            if level.quantity <= 0:
                self._bids.pop(
                    level.price,
                    None,
                )
            else:
                self._bids[level.price] = level.quantity

        for level in update.asks:
            if level.quantity <= 0:
                self._asks.pop(
                    level.price,
                    None,
                )
            else:
                self._asks[level.price] = level.quantity

        self._last_update_id = update.final_update_id

    def build_order_book(self) -> OrderBook:
        if not self._initialized:
            raise RuntimeError(
                "order book reconstructor is not initialized"
            )

        bids = [
            OrderBookLevel(
                price=price,
                quantity=quantity,
            )
            for price, quantity in self._bids.items()
            if quantity > 0
        ]

        asks = [
            OrderBookLevel(
                price=price,
                quantity=quantity,
            )
            for price, quantity in self._asks.items()
            if quantity > 0
        ]

        bids.sort(
            key=lambda level: level.price,
            reverse=True,
        )

        asks.sort(
            key=lambda level: level.price,
        )

        return OrderBook(
            exchange=self.exchange,
            symbol=self.symbol,
            bids=bids,
            asks=asks,
            received_at=order_book_received_at(),
        )


def order_book_received_at():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
