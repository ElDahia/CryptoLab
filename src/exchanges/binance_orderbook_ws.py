import json
import threading
from datetime import datetime, timezone
from typing import Callable

import websocket

from src.exchanges.models import OrderBook, OrderBookLevel


class BinanceOrderBookWebSocket:
    """
    Live Binance order book WebSocket client.

    Receives real-time depth updates and converts them
    into normalized OrderBook objects.

    This first implementation is intentionally focused
    on maintaining the latest local book state.
    Sequence validation and snapshot synchronization
    will be added in the reconstruction layer.
    """

    BASE_URL = "wss://stream.binance.com:9443/ws"

    def __init__(
        self,
        symbol: str = "BTC/USDT",
    ):
        self.symbol = symbol

        self.exchange_symbol = (
            symbol.replace("/", "").lower()
        )

        self.url = (
            f"{self.BASE_URL}/"
            f"{self.exchange_symbol}@depth@100ms"
        )

        self._socket = None
        self._thread = None
        self._running = False

        self._on_order_book: Callable[
            [OrderBook],
            None,
        ] | None = None

        self._bids: dict[float, float] = {}
        self._asks: dict[float, float] = {}

        self._received_count = 0
        self._error_count = 0

        self._last_update_id: int | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def received_count(self) -> int:
        return self._received_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def last_update_id(self) -> int | None:
        return self._last_update_id

    def _build_order_book(self) -> OrderBook:
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
            exchange="binance",
            symbol=self.symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )

    def _handle_message(
        self,
        message: str,
    ) -> None:
        data = json.loads(message)

        first_update_id = int(data["U"])
        final_update_id = int(data["u"])

        self._last_update_id = final_update_id

        for price, quantity in data["b"]:
            price_value = float(price)
            quantity_value = float(quantity)

            if quantity_value == 0:
                self._bids.pop(
                    price_value,
                    None,
                )
            else:
                self._bids[price_value] = quantity_value

        for price, quantity in data["a"]:
            price_value = float(price)
            quantity_value = float(quantity)

            if quantity_value == 0:
                self._asks.pop(
                    price_value,
                    None,
                )
            else:
                self._asks[price_value] = quantity_value

        self._received_count += 1

        order_book = self._build_order_book()

        if self._on_order_book is not None:
            self._on_order_book(order_book)

    def _on_open(
        self,
        ws,
    ) -> None:
        self._running = True

    def _on_message(
        self,
        ws,
        message: str,
    ) -> None:
        try:
            self._handle_message(message)
        except Exception:
            self._error_count += 1

    def _on_error(
        self,
        ws,
        error,
    ) -> None:
        self._error_count += 1

    def _on_close(
        self,
        ws,
        close_status_code,
        close_msg,
    ) -> None:
        self._running = False

    def start(
        self,
        on_order_book: Callable[
            [OrderBook],
            None,
        ] | None = None,
    ) -> None:
        if self._running:
            raise RuntimeError(
                "Binance order book WebSocket is already running"
            )

        self._on_order_book = on_order_book

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )

        self._thread.start()

    def _run(self) -> None:
        self._socket = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._socket.run_forever()

    def stop(self) -> None:
        self._running = False

        if self._socket is not None:
            self._socket.close()

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            self._thread.join(timeout=5)