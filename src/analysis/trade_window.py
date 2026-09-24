from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.microstructure import MarketTrade


@dataclass(frozen=True)
class TradeWindowStats:
    """
    Aggregated statistics for a rolling trade window.
    """

    exchange: str
    symbol: str

    window_seconds: float

    trade_count: int

    buy_volume: float
    sell_volume: float
    net_volume: float

    buy_notional: float
    sell_notional: float
    net_notional: float

    buy_ratio: float
    sell_ratio: float

    cvd: float

    first_trade_at: datetime | None
    last_trade_at: datetime | None


class TradeWindow:
    """
    Rolling time-based buffer for executed market trades.

    The window is anchored to current UTC time.

    Trades older than the configured window are ignored.

    Small clock differences between the local machine and
    an exchange server are tolerated through clock-skew
    tolerance.
    """

    def __init__(
        self,
        window_seconds: float = 5.0,
        clock_skew_tolerance_seconds: float = 1.0,
    ):
        if window_seconds <= 0:
            raise ValueError(
                "window_seconds must be greater than zero"
            )

        if clock_skew_tolerance_seconds < 0:
            raise ValueError(
                "clock_skew_tolerance_seconds must not be negative"
            )

        self.window_seconds = window_seconds

        self.clock_skew_tolerance_seconds = (
            clock_skew_tolerance_seconds
        )

        self._trades: deque[MarketTrade] = deque()

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _remove_expired(
        self,
        now: datetime | None = None,
    ) -> None:
        """
        Remove trades that are older than the rolling window.
        """

        if now is None:
            now = self._now()

        cutoff = (
            now.timestamp()
            - self.window_seconds
        )

        while self._trades:
            oldest_trade = self._trades[0]

            if oldest_trade.timestamp.timestamp() >= cutoff:
                break

            self._trades.popleft()

    def add(
        self,
        trade: MarketTrade,
    ) -> bool:
        """
        Add a trade to the rolling window.

        Returns True if the trade was accepted.

        Returns False if the trade is already outside
        the configured rolling window.
        """

        now = self._now()

        self._remove_expired(now=now)

        age_seconds = (
            now - trade.timestamp
        ).total_seconds()

        if (
            age_seconds
            < -self.clock_skew_tolerance_seconds
        ):
            raise ValueError(
                "trade timestamp is too far in the future"
            )

        if age_seconds > self.window_seconds:
            return False

        self._trades.append(trade)

        return True

    def add_many(
        self,
        trades: list[MarketTrade],
    ) -> int:
        """
        Add multiple trades to the rolling window.

        Returns the number of accepted trades.
        """

        accepted_count = 0

        for trade in trades:
            if self.add(trade):
                accepted_count += 1

        return accepted_count

    def clear(self) -> None:
        """
        Remove all trades from the window.
        """

        self._trades.clear()

    @property
    def trade_count(self) -> int:
        """
        Number of trades currently inside the window.
        """

        self._remove_expired()

        return len(self._trades)

    def trades(self) -> list[MarketTrade]:
        """
        Return a snapshot of trades currently inside
        the rolling window.
        """

        self._remove_expired()

        return list(self._trades)

    def stats(self) -> TradeWindowStats:
        """
        Calculate aggregated statistics for the current
        rolling window.
        """

        now = self._now()

        self._remove_expired(now=now)

        if not self._trades:
            return TradeWindowStats(
                exchange="",
                symbol="",

                window_seconds=self.window_seconds,

                trade_count=0,

                buy_volume=0.0,
                sell_volume=0.0,
                net_volume=0.0,

                buy_notional=0.0,
                sell_notional=0.0,
                net_notional=0.0,

                buy_ratio=0.0,
                sell_ratio=0.0,

                cvd=0.0,

                first_trade_at=None,
                last_trade_at=None,
            )

        first_trade = self._trades[0]
        last_trade = self._trades[-1]

        buy_volume = 0.0
        sell_volume = 0.0

        buy_notional = 0.0
        sell_notional = 0.0

        for trade in self._trades:
            if trade.is_buyer_maker:
                sell_volume += trade.quantity
                sell_notional += trade.notional
            else:
                buy_volume += trade.quantity
                buy_notional += trade.notional

        net_volume = (
            buy_volume
            - sell_volume
        )

        net_notional = (
            buy_notional
            - sell_notional
        )

        total_volume = (
            buy_volume
            + sell_volume
        )

        if total_volume == 0:
            buy_ratio = 0.0
            sell_ratio = 0.0
        else:
            buy_ratio = (
                buy_volume
                / total_volume
            )

            sell_ratio = (
                sell_volume
                / total_volume
            )

        return TradeWindowStats(
            exchange=first_trade.exchange,
            symbol=first_trade.symbol,

            window_seconds=self.window_seconds,

            trade_count=len(self._trades),

            buy_volume=buy_volume,
            sell_volume=sell_volume,
            net_volume=net_volume,

            buy_notional=buy_notional,
            sell_notional=sell_notional,
            net_notional=net_notional,

            buy_ratio=buy_ratio,
            sell_ratio=sell_ratio,

            cvd=net_volume,

            first_trade_at=first_trade.timestamp,
            last_trade_at=last_trade.timestamp,
        )