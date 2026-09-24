from __future__ import annotations

import time
from threading import Lock
from typing import Optional

from src.exchanges.binance_orderbook_sync import BinanceOrderBookSync
from src.exchanges.models import OrderBook


class V6LiveMarketFeed:
    def __init__(
        self,
        symbol: str = "BTC/USDT",
        snapshot_limit: int = 1000,
    ) -> None:
        self.symbol = symbol
        self.snapshot_limit = snapshot_limit

        self._sync = BinanceOrderBookSync(
            symbol=symbol,
            snapshot_limit=snapshot_limit,
        )

        self._lock = Lock()
        self._latest_order_book: Optional[OrderBook] = None
        self._update_count = 0
        self._started_at: Optional[float] = None

    def _on_order_book(self, order_book: OrderBook) -> None:
        with self._lock:
            self._latest_order_book = order_book
            self._update_count += 1

    def start(self) -> None:
        if self._started_at is not None:
            raise RuntimeError(
                "V6 live market feed is already running"
            )

        self._started_at = time.monotonic()

        self._sync.start(
            on_order_book=self._on_order_book,
        )

    def stop(self) -> None:
        self._sync.stop()

        with self._lock:
            self._started_at = None

    @property
    def is_running(self) -> bool:
        return self._sync.is_running

    @property
    def is_synchronized(self) -> bool:
        return self._sync.is_synchronized

    @property
    def latest_order_book(self) -> Optional[OrderBook]:
        with self._lock:
            return self._latest_order_book

    @property
    def update_count(self) -> int:
        with self._lock:
            return self._update_count

    @property
    def received_event_count(self) -> int:
        return self._sync.received_events

    @property
    def applied_event_count(self) -> int:
        return self._sync.applied_events

    @property
    def gap_count(self) -> int:
        return self._sync.gap_count

    @property
    def resync_count(self) -> int:
        return self._sync.resync_count

    @property
    def error_count(self) -> int:
        return self._sync.error_count

    def get_latest_order_book(self) -> OrderBook:
        order_book = self.latest_order_book

        if order_book is None:
            raise RuntimeError(
                "No validated order book is available yet"
            )

        return order_book
