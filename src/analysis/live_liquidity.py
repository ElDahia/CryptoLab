from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.models import OrderBook
from src.analysis.liquidity import (
    LiquidityMetrics,
    calculate_liquidity_metrics,
)
from src.analysis.liquidity_profile import (
    LiquidityProfile,
    calculate_liquidity_profile,
)


@dataclass(frozen=True)
class LiveLiquidityState:
    """
    Latest live liquidity state for one market.

    Combines basic liquidity metrics with
    distance-based liquidity profiling.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    metrics: LiquidityMetrics
    profile: LiquidityProfile

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
    def bid_depth_quantity(self) -> float:
        return self.metrics.bid_depth_quantity

    @property
    def ask_depth_quantity(self) -> float:
        return self.metrics.ask_depth_quantity

    @property
    def bid_depth_notional(self) -> float:
        return self.metrics.bid_depth_notional

    @property
    def ask_depth_notional(self) -> float:
        return self.metrics.ask_depth_notional

    @property
    def total_depth_quantity(self) -> float:
        return self.metrics.total_depth_quantity

    @property
    def total_depth_notional(self) -> float:
        return self.metrics.total_depth_notional

    @property
    def bid_liquidity_ratio(self) -> float:
        return self.metrics.bid_liquidity_ratio

    @property
    def ask_liquidity_ratio(self) -> float:
        return self.metrics.ask_liquidity_ratio

    @property
    def bid_notional_ratio(self) -> float:
        return self.metrics.bid_notional_ratio

    @property
    def ask_notional_ratio(self) -> float:
        return self.metrics.ask_notional_ratio

    @property
    def bid_concentration(self) -> float:
        return self.metrics.bid_concentration

    @property
    def ask_concentration(self) -> float:
        return self.metrics.ask_concentration

    @property
    def liquidity_profile(self) -> LiquidityProfile:
        return self.profile

    def age_seconds(self) -> float:
        return (
            datetime.now(timezone.utc)
            - self.timestamp
        ).total_seconds()

    def is_fresh(
        self,
        max_age_seconds: float = 5.0,
    ) -> bool:
        return self.age_seconds() <= max_age_seconds


class LiveLiquidityEngine:
    """
    Converts validated live order books into
    continuously updated liquidity state.

    The engine calculates both standard liquidity
    metrics and distance-based liquidity profiles.
    """

    def __init__(
        self,
        depth_levels: int = 5,
        profile_distances_bps: tuple[float, ...] = (
            1.0,
            2.0,
            5.0,
            10.0,
            25.0,
            50.0,
            100.0,
        ),
    ):
        if depth_levels <= 0:
            raise ValueError(
                "depth_levels must be greater than zero"
            )

        if not profile_distances_bps:
            raise ValueError(
                "profile_distances_bps must not be empty"
            )

        self.depth_levels = depth_levels

        self.profile_distances_bps = (
            tuple(profile_distances_bps)
        )

        self._latest_state: (
            LiveLiquidityState | None
        ) = None

        self._update_count = 0

    @property
    def latest_state(
        self,
    ) -> LiveLiquidityState | None:
        return self._latest_state

    @property
    def update_count(self) -> int:
        return self._update_count

    def update(
        self,
        order_book: OrderBook,
    ) -> LiveLiquidityState:
        """
        Process one validated live order book.
        """

        metrics = calculate_liquidity_metrics(
            order_book=order_book,
            depth_levels=self.depth_levels,
        )

        profile = calculate_liquidity_profile(
            order_book=order_book,
            distances_bps=self.profile_distances_bps,
        )

        state = LiveLiquidityState(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            timestamp=order_book.received_at,
            metrics=metrics,
            profile=profile,
        )

        self._latest_state = state
        self._update_count += 1

        return state

    def reset(self) -> None:
        """
        Clear the current live liquidity state.
        """

        self._latest_state = None
        self._update_count = 0