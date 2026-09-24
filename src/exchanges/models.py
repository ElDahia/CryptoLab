from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class Quote:
    exchange: str
    symbol: str
    price: float
    received_at: datetime

    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self.received_at).total_seconds()

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        return self.age_seconds() <= max_age_seconds


@dataclass(frozen=True)
class OrderBookLevel:
    price: float
    quantity: float


@dataclass(frozen=True)
class OrderBook:
    exchange: str
    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    received_at: datetime

    @property
    def best_bid(self) -> OrderBookLevel:
        if not self.bids:
            raise ValueError("Order book contains no bids")

        return max(
            self.bids,
            key=lambda level: level.price,
        )

    @property
    def best_ask(self) -> OrderBookLevel:
        if not self.asks:
            raise ValueError("Order book contains no asks")

        return min(
            self.asks,
            key=lambda level: level.price,
        )

    @property
    def spread(self) -> float:
        return (
            self.best_ask.price
            - self.best_bid.price
        )

    @property
    def spread_percent(self) -> float:
        if self.best_bid.price <= 0:
            raise ValueError(
                "Best bid price must be greater than zero"
            )

        return (
            self.spread
            / self.best_bid.price
        ) * 100

    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self.received_at).total_seconds()

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        return self.age_seconds() <= max_age_seconds