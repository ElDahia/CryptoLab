import json
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable

import requests
import websocket

from src.analysis.live_microstructure import (
    LiveMicrostructureEngine,
    LiveMicrostructureState,
)
from src.exchanges.models import OrderBook, OrderBookLevel
from src.exchanges.order_book_reconstructor import (
    OrderBookReconstructor,
    OrderBookUpdate,
)


class BinanceOrderBookSync:
    """
    Binance local order book synchronizer.

    Coordinates:

    REST snapshot
        +
    WebSocket depth updates
        +
    sequence validation
        +
    local book reconstruction
        +
    automatic resynchronization after sequence gaps
        +
    live microstructure calculation
    """

    BASE_REST_URL = "https://api.binance.com/api/v3"
    BASE_WS_URL = "wss://stream.binance.com:9443/ws"

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        snapshot_limit: int = 1000,
        max_resync_attempts: int = 3,
        resync_retry_delay: float = 0.25,
        microstructure_depth_levels: int = 5,
        microstructure_decay: float = 1.0,
    ):
        if snapshot_limit <= 0:
            raise ValueError(
                "snapshot_limit must be greater than zero"
            )

        if snapshot_limit > 5000:
            raise ValueError(
                "snapshot_limit must not exceed 5000"
            )

        if max_resync_attempts <= 0:
            raise ValueError(
                "max_resync_attempts must be greater than zero"
            )

        if resync_retry_delay < 0:
            raise ValueError(
                "resync_retry_delay must not be negative"
            )

        if microstructure_depth_levels <= 0:
            raise ValueError(
                "microstructure_depth_levels must be greater than zero"
            )

        if microstructure_decay <= 0:
            raise ValueError(
                "microstructure_decay must be greater than zero"
            )

        self.symbol = symbol

        self.exchange_symbol = (
            symbol.replace("/", "").lower()
        )

        self.snapshot_limit = snapshot_limit
        self.max_resync_attempts = max_resync_attempts
        self.resync_retry_delay = resync_retry_delay

        self.ws_url = (
            f"{self.BASE_WS_URL}/"
            f"{self.exchange_symbol}@depth@100ms"
        )

        self._socket = None
        self._thread = None
        self._processing_thread = None

        self._running = False
        self._synchronized = False

        self._events: deque[dict] = deque()
        self._lock = threading.Lock()

        self._reconstructor = OrderBookReconstructor(
            exchange="binance",
            symbol=symbol,
        )

        self._microstructure_engine = (
            LiveMicrostructureEngine(
                depth_levels=microstructure_depth_levels,
                decay=microstructure_decay,
            )
        )

        self._last_update_id: int | None = None

        self._received_events = 0
        self._applied_events = 0
        self._skipped_events = 0

        self._gap_count = 0
        self._resync_count = 0
        self._resync_failure_count = 0
        self._error_count = 0

        self._on_order_book: Callable[
            [OrderBook],
            None,
        ] | None = None

        self._on_microstructure: Callable[
            [LiveMicrostructureState],
            None,
        ] | None = None

        self._worker_stop = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_synchronized(self) -> bool:
        return self._synchronized

    @property
    def received_events(self) -> int:
        return self._received_events

    @property
    def applied_events(self) -> int:
        return self._applied_events

    @property
    def skipped_events(self) -> int:
        return self._skipped_events

    @property
    def gap_count(self) -> int:
        return self._gap_count

    @property
    def resync_count(self) -> int:
        return self._resync_count

    @property
    def resync_failure_count(self) -> int:
        return self._resync_failure_count

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def last_update_id(self) -> int | None:
        return self._last_update_id

    @property
    def latest_microstructure(
        self,
    ) -> LiveMicrostructureState | None:
        return self._microstructure_engine.latest_state

    @property
    def microstructure_update_count(self) -> int:
        return self._microstructure_engine.update_count

    def _on_open(self, ws) -> None:
        self._running = True

    def _on_message(
        self,
        ws,
        message: str,
    ) -> None:
        try:
            data = json.loads(message)

            if "U" not in data or "u" not in data:
                return

            with self._lock:
                self._events.append(data)

            self._received_events += 1

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

    def _run_websocket(self) -> None:
        self._socket = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._socket.run_forever()

    def _fetch_snapshot(
        self,
    ) -> tuple[OrderBook, int]:

        response = requests.get(
            f"{self.BASE_REST_URL}/depth",
            params={
                "symbol": self.symbol.replace("/", ""),
                "limit": self.snapshot_limit,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        bids = [
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in data["bids"]
            if float(quantity) > 0
        ]

        asks = [
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in data["asks"]
            if float(quantity) > 0
        ]

        order_book = OrderBook(
            exchange="binance",
            symbol=self.symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )

        return order_book, int(
            data["lastUpdateId"]
        )

    def _get_buffered_events(self) -> list[dict]:
        with self._lock:
            return list(self._events)

    def _clear_events_through(
        self,
        update_id: int,
    ) -> None:
        with self._lock:
            while self._events:
                event = self._events[0]

                if int(event["u"]) > update_id:
                    break

                self._events.popleft()

    def _find_bridge_event(
        self,
        snapshot_update_id: int,
    ) -> dict | None:

        events = self._get_buffered_events()

        for event in events:
            first_update_id = int(event["U"])
            final_update_id = int(event["u"])

            if final_update_id <= snapshot_update_id:
                continue

            if (
                first_update_id
                <= snapshot_update_id + 1
                <= final_update_id
            ):
                return event

        return None

    def _event_to_update(
        self,
        event: dict,
    ) -> OrderBookUpdate:

        return OrderBookUpdate(
            first_update_id=int(event["U"]),
            final_update_id=int(event["u"]),
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

    def _initialize_from_snapshot(
        self,
        snapshot: OrderBook,
        snapshot_update_id: int,
    ) -> None:

        self._reconstructor = OrderBookReconstructor(
            exchange="binance",
            symbol=self.symbol,
        )

        self._reconstructor.initialize_from_snapshot(
            order_book=snapshot,
            snapshot_update_id=snapshot_update_id,
        )

        self._microstructure_engine.reset()

        self._last_update_id = snapshot_update_id
        self._synchronized = False

    def synchronize(self) -> None:
        if not self._running:
            raise RuntimeError(
                "WebSocket must be running before synchronization"
            )

        snapshot, snapshot_update_id = (
            self._fetch_snapshot()
        )

        self._initialize_from_snapshot(
            snapshot=snapshot,
            snapshot_update_id=snapshot_update_id,
        )

        bridge_event = None

        deadline = time.time() + 5

        while (
            time.time() < deadline
            and self._running
        ):
            bridge_event = self._find_bridge_event(
                snapshot_update_id
            )

            if bridge_event is not None:
                break

            time.sleep(0.05)

        if bridge_event is None:
            raise RuntimeError(
                "could not find WebSocket bridge event"
            )

        bridge_update = self._event_to_update(
            bridge_event
        )

        self._reconstructor.apply_update(
            bridge_update
        )

        self._applied_events += 1

        self._last_update_id = (
            self._reconstructor.last_update_id
        )

        self._clear_events_through(
            self._last_update_id
        )

        self._synchronized = True

    def _resynchronize(self) -> bool:
        self._resync_count += 1

        self._synchronized = False

        for attempt in range(
            self.max_resync_attempts
        ):
            if not self._running:
                return False

            try:
                self.synchronize()

                return True

            except Exception:
                self._error_count += 1

                if (
                    attempt
                    < self.max_resync_attempts - 1
                ):
                    if self.resync_retry_delay > 0:
                        time.sleep(
                            self.resync_retry_delay
                        )

        self._resync_failure_count += 1

        return False

    def _update_microstructure(
        self,
        order_book: OrderBook,
    ) -> None:

        state = (
            self._microstructure_engine.update(
                order_book
            )
        )

        if self._on_microstructure is not None:
            self._on_microstructure(state)

    def _process_buffered_events(self) -> None:
        if not self._synchronized:
            return

        while self._running:

            with self._lock:
                if not self._events:
                    return

                event = self._events.popleft()

            final_update_id = int(event["u"])

            if (
                self._last_update_id is not None
                and final_update_id
                <= self._last_update_id
            ):
                self._skipped_events += 1
                continue

            first_update_id = int(event["U"])

            if (
                self._last_update_id is not None
                and first_update_id
                > self._last_update_id + 1
            ):
                self._gap_count += 1

                with self._lock:
                    self._events.appendleft(event)

                if not self._resynchronize():
                    return

                continue

            update = self._event_to_update(event)

            try:
                self._reconstructor.apply_update(
                    update
                )

                self._applied_events += 1

                self._last_update_id = (
                    self._reconstructor.last_update_id
                )

                order_book = (
                    self._reconstructor.build_order_book()
                )

                self._update_microstructure(
                    order_book
                )

                if self._on_order_book is not None:
                    self._on_order_book(
                        order_book
                    )

            except RuntimeError:
                self._gap_count += 1

                with self._lock:
                    self._events.appendleft(event)

                if not self._resynchronize():
                    return

    def _processing_loop(self) -> None:
        while not self._worker_stop.is_set():

            if not self._running:
                time.sleep(0.01)
                continue

            if not self._synchronized:
                time.sleep(0.01)
                continue

            try:
                self._process_buffered_events()

            except Exception:
                self._error_count += 1

            time.sleep(0.01)

    def start(
        self,
        on_order_book: Callable[
            [OrderBook],
            None,
        ] | None = None,
        on_microstructure: Callable[
            [LiveMicrostructureState],
            None,
        ] | None = None,
    ) -> None:

        if self._running:
            raise RuntimeError(
                "Binance order book sync is already running"
            )

        self._on_order_book = on_order_book
        self._on_microstructure = on_microstructure

        self._worker_stop.clear()

        self._thread = threading.Thread(
            target=self._run_websocket,
            daemon=True,
        )

        self._thread.start()

        deadline = time.time() + 5

        while not self._running:
            if time.time() >= deadline:
                raise RuntimeError(
                    "WebSocket did not start within 5 seconds"
                )

            time.sleep(0.01)

        self.synchronize()

        self._processing_thread = threading.Thread(
            target=self._processing_loop,
            daemon=True,
        )

        self._processing_thread.start()

    def get_order_book(self) -> OrderBook:
        if not self._synchronized:
            raise RuntimeError(
                "order book is not synchronized"
            )

        return self._reconstructor.build_order_book()

    def get_microstructure(
        self,
    ) -> LiveMicrostructureState:
        if not self._synchronized:
            raise RuntimeError(
                "order book is not synchronized"
            )

        state = self.latest_microstructure

        if state is None:
            raise RuntimeError(
                "microstructure state is not available"
            )

        return state

    def stop(self) -> None:
        self._running = False

        self._worker_stop.set()

        if self._socket is not None:
            self._socket.close()

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            self._thread.join(timeout=5)

        processing_thread = getattr(
            self,
            "_processing_thread",
            None,
        )

        if (
            processing_thread is not None
            and processing_thread.is_alive()
        ):
            processing_thread.join(timeout=5)

        self._synchronized = False