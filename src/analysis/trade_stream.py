import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from src.analysis.market_activity import (
    MarketActivityEngine,
    MarketActivityState,
)
from src.analysis.microstructure import MarketTrade
from src.analysis.trade_deduplicator import TradeDeduplicator


@dataclass(frozen=True)
class TradeStreamStats:
    """
    Runtime statistics for a trade stream.
    """

    started_at: datetime
    last_trade_at: datetime | None

    received_count: int
    emitted_count: int
    duplicate_count: int
    rejected_count: int
    error_count: int

    elapsed_seconds: float

    @property
    def trades_per_second(self) -> float:
        if self.elapsed_seconds <= 0:
            return 0.0

        return self.emitted_count / self.elapsed_seconds

    @property
    def duplicate_ratio(self) -> float:
        if self.received_count == 0:
            return 0.0

        return self.duplicate_count / self.received_count


class TradeStream:
    """
    Generic trade-processing stream.

    Trades can enter the stream through:

    - REST polling
    - WebSocket callbacks
    - Any other producer

    Every trade passes through:

    Trade
        ↓
    Deduplication
        ↓
    Rolling Activity Window
        ↓
    Market Activity Engine
    """

    def __init__(
        self,
        source: Callable[[], Iterable[MarketTrade]] | None = None,
        interval_seconds: float = 1.0,
        deduplicator: TradeDeduplicator | None = None,
        activity_engine: MarketActivityEngine | None = None,
    ):
        if interval_seconds <= 0:
            raise ValueError(
                "interval_seconds must be greater than zero"
            )

        self.source = source
        self.interval_seconds = interval_seconds

        self.deduplicator = (
            deduplicator
            if deduplicator is not None
            else TradeDeduplicator()
        )

        self.activity_engine = (
            activity_engine
            if activity_engine is not None
            else MarketActivityEngine()
        )

        self._running = False

        self._started_at: datetime | None = None
        self._last_trade_at: datetime | None = None

        self._received_count = 0
        self._emitted_count = 0
        self._duplicate_count = 0
        self._rejected_count = 0
        self._error_count = 0

    @property
    def is_running(self) -> bool:
        """
        Return True when the stream is running.
        """

        return self._running

    def start(self) -> None:
        """
        Start the processing lifecycle.

        This method marks the stream as active.

        It does not start a producer.
        """

        if self._running:
            raise RuntimeError(
                "trade stream is already running"
            )

        self._running = True
        self._started_at = datetime.now(timezone.utc)

    def stop(self) -> None:
        """
        Stop the stream.
        """

        self._running = False

    def reset(self) -> None:
        """
        Reset runtime state and statistics.

        The stream must not be running.
        """

        if self._running:
            raise RuntimeError(
                "cannot reset a running trade stream"
            )

        self.deduplicator.clear()
        self.activity_engine.clear()

        self._started_at = None
        self._last_trade_at = None

        self._received_count = 0
        self._emitted_count = 0
        self._duplicate_count = 0
        self._rejected_count = 0
        self._error_count = 0

    def process_trade(
        self,
        trade: MarketTrade,
        on_trade: Callable[[MarketTrade], None] | None = None,
        on_activity: Callable[
            [MarketActivityState],
            None,
        ] | None = None,
    ) -> bool:
        """
        Process one incoming trade.

        Returns True when the trade successfully enters
        the rolling activity engine.

        Returns False when the trade is a duplicate or
        outside the rolling window.
        """

        self._received_count += 1

        try:
            if not self.deduplicator.add(trade):
                self._duplicate_count += 1
                return False

            accepted = self.activity_engine.add_trade(
                trade
            )

            if not accepted:
                self._rejected_count += 1
                return False

            self._last_trade_at = trade.timestamp
            self._emitted_count += 1

            if on_trade is not None:
                on_trade(trade)

            if on_activity is not None:
                state = self.activity_engine.build_state()

                if state is not None:
                    on_activity(state)

            return True

        except Exception:
            self._error_count += 1
            return False

    def process_trades(
        self,
        trades: Iterable[MarketTrade],
        on_trade: Callable[[MarketTrade], None] | None = None,
        on_activity: Callable[
            [MarketActivityState],
            None,
        ] | None = None,
    ) -> int:
        """
        Process multiple incoming trades.

        Returns the number of accepted trades.
        """

        accepted_count = 0

        for trade in trades:
            if self.process_trade(
                trade=trade,
                on_trade=on_trade,
                on_activity=on_activity,
            ):
                accepted_count += 1

        return accepted_count

    def stats(self) -> TradeStreamStats:
        """
        Return current stream statistics.
        """

        now = datetime.now(timezone.utc)

        if self._started_at is None:
            elapsed_seconds = 0.0
        else:
            elapsed_seconds = (
                now - self._started_at
            ).total_seconds()

        return TradeStreamStats(
            started_at=(
                self._started_at
                if self._started_at is not None
                else now
            ),
            last_trade_at=self._last_trade_at,

            received_count=self._received_count,
            emitted_count=self._emitted_count,
            duplicate_count=self._duplicate_count,
            rejected_count=self._rejected_count,
            error_count=self._error_count,

            elapsed_seconds=elapsed_seconds,
        )

    def activity_state(
        self,
    ) -> MarketActivityState | None:
        """
        Return the current market activity state.
        """

        return self.activity_engine.build_state()

    def run(
        self,
        on_trade: Callable[[MarketTrade], None] | None = None,
        on_activity: Callable[
            [MarketActivityState],
            None,
        ] | None = None,
        max_cycles: int | None = None,
    ) -> TradeStreamStats:
        """
        Run a polling-based trade stream.

        This method is retained for REST-style sources.

        WebSocket producers can use process_trade() directly.
        """

        if self.source is None:
            raise RuntimeError(
                "trade stream has no polling source"
            )

        if max_cycles is not None and max_cycles <= 0:
            raise ValueError(
                "max_cycles must be greater than zero"
            )

        self.start()

        cycles = 0

        try:
            while self._running:
                try:
                    trades = self.source()

                    self.process_trades(
                        trades=trades,
                        on_trade=on_trade,
                        on_activity=on_activity,
                    )

                except Exception:
                    self._error_count += 1

                cycles += 1

                if (
                    max_cycles is not None
                    and cycles >= max_cycles
                ):
                    break

                if not self._running:
                    break

                time.sleep(self.interval_seconds)

        finally:
            self._running = False

        return self.stats()