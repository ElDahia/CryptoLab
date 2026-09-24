from dataclasses import dataclass
from datetime import datetime

from src.analysis.microstructure import MarketTrade
from src.analysis.trade_intensity import (
    TradeIntensityMetrics,
    calculate_trade_intensity,
)
from src.analysis.trade_window import (
    TradeWindow,
    TradeWindowStats,
)


@dataclass(frozen=True)
class MarketActivityState:
    """
    Combined real-time market activity state.

    This state is built from unique trades currently
    inside a rolling time window.
    """

    exchange: str
    symbol: str

    timestamp: datetime

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

    trades_per_second: float
    volume_per_second: float
    notional_per_second: float

    average_trade_size: float
    average_trade_notional: float

    largest_trade_volume: float
    largest_trade_notional: float

    def is_buy_dominant(self) -> bool:
        return self.buy_volume > self.sell_volume

    def is_sell_dominant(self) -> bool:
        return self.sell_volume > self.buy_volume

    @property
    def has_activity(self) -> bool:
        return self.trade_count > 0


class MarketActivityEngine:
    """
    Builds a combined market-activity state from a
    rolling stream of executed trades.
    """

    def __init__(
        self,
        window_seconds: float = 5.0,
    ):
        if window_seconds <= 0:
            raise ValueError(
                "window_seconds must be greater than zero"
            )

        self.window = TradeWindow(
            window_seconds=window_seconds,
        )

    @property
    def window_seconds(self) -> float:
        return self.window.window_seconds

    def add_trade(
        self,
        trade: MarketTrade,
    ) -> bool:
        return self.window.add(trade)

    def add_trades(
        self,
        trades: list[MarketTrade],
    ) -> int:
        return self.window.add_many(trades)

    def clear(self) -> None:
        self.window.clear()

    def trades(self) -> list[MarketTrade]:
        return self.window.trades()

    def build_state(self) -> MarketActivityState | None:
        trades = self.window.trades()

        if not trades:
            return None

        window_stats: TradeWindowStats = (
            self.window.stats()
        )

        intensity: TradeIntensityMetrics = (
            calculate_trade_intensity(
                trades=trades,
                window_seconds=self.window_seconds,
            )
        )

        return MarketActivityState(
            exchange=window_stats.exchange,
            symbol=window_stats.symbol,

            timestamp=(
                window_stats.last_trade_at
                if window_stats.last_trade_at is not None
                else trades[-1].timestamp
            ),

            window_seconds=self.window_seconds,

            trade_count=window_stats.trade_count,

            buy_volume=window_stats.buy_volume,
            sell_volume=window_stats.sell_volume,
            net_volume=window_stats.net_volume,

            buy_notional=window_stats.buy_notional,
            sell_notional=window_stats.sell_notional,
            net_notional=window_stats.net_notional,

            buy_ratio=window_stats.buy_ratio,
            sell_ratio=window_stats.sell_ratio,

            cvd=window_stats.cvd,

            trades_per_second=(
                intensity.trades_per_second
            ),

            volume_per_second=(
                intensity.volume_per_second
            ),

            notional_per_second=(
                intensity.notional_per_second
            ),

            average_trade_size=(
                intensity.average_trade_size
            ),

            average_trade_notional=(
                intensity.average_trade_notional
            ),

            largest_trade_volume=(
                intensity.largest_trade_volume
            ),

            largest_trade_notional=(
                intensity.largest_trade_notional
            ),
        )