from collections import deque
from dataclasses import dataclass

from src.analysis.microstructure import MarketTrade


@dataclass(frozen=True)
class DeduplicationStats:
    """
    Statistics for the trade deduplication engine.
    """

    received_count: int
    emitted_count: int
    duplicate_count: int
    cache_size: int

    @property
    def unique_ratio(self) -> float:
        if self.received_count == 0:
            return 0.0

        return self.emitted_count / self.received_count


class TradeDeduplicator:
    """
    Removes repeated trades from a market-trade stream.

    The deduplicator prefers an exchange-native trade ID
    when available.

    If no native trade ID exists, it falls back to a
    deterministic trade fingerprint.
    """

    def __init__(
        self,
        max_cache_size: int = 100_000,
    ):
        if max_cache_size <= 0:
            raise ValueError(
                "max_cache_size must be greater than zero"
            )

        self.max_cache_size = max_cache_size

        self._seen: set[str] = set()
        self._order: deque[str] = deque()

        self._received_count = 0
        self._emitted_count = 0
        self._duplicate_count = 0

    def _identity(
        self,
        trade: MarketTrade,
    ) -> str:
        """
        Build a stable identity for a trade.
        """

        trade_id = getattr(
            trade,
            "trade_id",
            None,
        )

        if trade_id is not None:
            return (
                f"{trade.exchange}:"
                f"{trade.symbol}:"
                f"id:{trade_id}"
            )

        return (
            f"{trade.exchange}:"
            f"{trade.symbol}:"
            f"fallback:"
            f"{trade.timestamp.isoformat()}:"
            f"{trade.price}:"
            f"{trade.quantity}:"
            f"{trade.is_buyer_maker}"
        )

    def seen(
        self,
        trade: MarketTrade,
    ) -> bool:
        """
        Check whether a trade has already been observed.
        """

        return self._identity(trade) in self._seen

    def add(
        self,
        trade: MarketTrade,
    ) -> bool:
        """
        Add a trade to the deduplication cache.

        Returns True if the trade is new.
        Returns False if the trade is a duplicate.
        """

        identity = self._identity(trade)

        self._received_count += 1

        if identity in self._seen:
            self._duplicate_count += 1
            return False

        if len(self._seen) >= self.max_cache_size:
            oldest_identity = self._order.popleft()
            self._seen.remove(oldest_identity)

        self._seen.add(identity)
        self._order.append(identity)

        self._emitted_count += 1

        return True

    def filter(
        self,
        trades: list[MarketTrade],
    ) -> list[MarketTrade]:
        """
        Return only trades that have not been seen before.
        """

        unique_trades = []

        for trade in trades:
            if self.add(trade):
                unique_trades.append(trade)

        return unique_trades

    def stats(self) -> DeduplicationStats:
        """
        Return current deduplication statistics.
        """

        return DeduplicationStats(
            received_count=self._received_count,
            emitted_count=self._emitted_count,
            duplicate_count=self._duplicate_count,
            cache_size=len(self._seen),
        )

    def clear(self) -> None:
        """
        Clear the deduplication cache and statistics.
        """

        self._seen.clear()
        self._order.clear()

        self._received_count = 0
        self._emitted_count = 0
        self._duplicate_count = 0