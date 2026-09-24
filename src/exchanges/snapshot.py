from dataclasses import dataclass
from datetime import datetime

from src.exchanges.models import Quote


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    cycle_started_at: datetime
    completed_at: datetime
    quotes: list[Quote]

    @property
    def duration_seconds(self) -> float:
        return (
            self.completed_at - self.cycle_started_at
        ).total_seconds()

    @property
    def quote_count(self) -> int:
        return len(self.quotes)

    @property
    def highest_quote(self) -> Quote:
        if not self.quotes:
            raise ValueError("Snapshot contains no quotes")

        return max(
            self.quotes,
            key=lambda quote: quote.price,
        )

    @property
    def lowest_quote(self) -> Quote:
        if not self.quotes:
            raise ValueError("Snapshot contains no quotes")

        return min(
            self.quotes,
            key=lambda quote: quote.price,
        )

    @property
    def spread(self) -> float:
        return (
            self.highest_quote.price
            - self.lowest_quote.price
        )

    @property
    def spread_percent(self) -> float:
        lowest_price = self.lowest_quote.price

        if lowest_price <= 0:
            raise ValueError(
                "Lowest price must be greater than zero"
            )

        return (
            self.spread
            / lowest_price
        ) * 100

    @property
    def best_buy_quote(self) -> Quote:
        """
        The exchange with the lowest available price.
        """
        return self.lowest_quote

    @property
    def best_sell_quote(self) -> Quote:
        """
        The exchange with the highest available price.
        """
        return self.highest_quote