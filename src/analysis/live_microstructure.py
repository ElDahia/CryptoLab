from dataclasses import dataclass
from datetime import datetime

from src.exchanges.models import OrderBook
from src.analysis.microstructure import (
    OrderBookMetrics,
    calculate_order_book_metrics,
)


@dataclass(frozen=True)
class LiveMicrostructureState:
    """
    Latest live microstructure state for one market.
    """

    exchange: str
    symbol: str
    timestamp: datetime
    metrics: OrderBookMetrics

    @property
    def best_bid(self) -> float:
        return self.metrics.best_bid

    @property
    def best_ask(self) -> float:
        return self.metrics.best_ask

    @property
    def mid_price(self) -> float:
        return self.metrics.mid_price

    @property
    def spread(self) -> float:
        return self.metrics.spread

    @property
    def spread_percent(self) -> float:
        return self.metrics.spread_percent

    @property
    def imbalance(self) -> float:
        return self.metrics.imbalance

    @property
    def weighted_imbalance(self) -> float:
        return self.metrics.weighted_imbalance


class LiveMicrostructureEngine:
    """
    Converts validated live order books into
    continuously updated microstructure state.
    """

    def __init__(
        self,
        depth_levels: int = 5,
        decay: float = 1.0,
    ):
        if depth_levels <= 0:
            raise ValueError(
                "depth_levels must be greater than zero"
            )

        if decay <= 0:
            raise ValueError(
                "decay must be greater than zero"
            )

        self.depth_levels = depth_levels
        self.decay = decay

        self._latest_state: LiveMicrostructureState | None = None
        self._update_count = 0

    @property
    def latest_state(
        self,
    ) -> LiveMicrostructureState | None:
        return self._latest_state

    @property
    def update_count(self) -> int:
        return self._update_count

    def update(
        self,
        order_book: OrderBook,
    ) -> LiveMicrostructureState:
        """
        Process one validated order book update.
        """

        metrics = calculate_order_book_metrics(
            order_book=order_book,
            depth_levels=self.depth_levels,
            decay=self.decay,
        )

        state = LiveMicrostructureState(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            timestamp=order_book.received_at,
            metrics=metrics,
        )

        self._latest_state = state
        self._update_count += 1

        return state

    def reset(self) -> None:
        """
        Clear the current live state.
        """

        self._latest_state = None
        self._update_count = 0