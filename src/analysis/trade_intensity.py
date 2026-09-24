from dataclasses import dataclass

from src.analysis.microstructure import MarketTrade


@dataclass(frozen=True)
class TradeIntensityMetrics:
    """
    Market activity metrics calculated from executed trades.
    """

    exchange: str
    symbol: str

    window_seconds: float

    trade_count: int

    volume: float
    notional: float

    trades_per_second: float
    volume_per_second: float
    notional_per_second: float

    average_trade_size: float
    average_trade_notional: float

    largest_trade_volume: float
    largest_trade_notional: float


def calculate_trade_intensity(
    trades: list[MarketTrade],
    window_seconds: float,
) -> TradeIntensityMetrics:
    """
    Calculate trading activity intensity over a fixed time window.
    """

    if window_seconds <= 0:
        raise ValueError(
            "window_seconds must be greater than zero"
        )

    if not trades:
        raise ValueError(
            "trades must not be empty"
        )

    exchange = trades[0].exchange
    symbol = trades[0].symbol

    trade_count = len(trades)

    volume = sum(
        trade.quantity
        for trade in trades
    )

    notional = sum(
        trade.notional
        for trade in trades
    )

    trades_per_second = (
        trade_count
        / window_seconds
    )

    volume_per_second = (
        volume
        / window_seconds
    )

    notional_per_second = (
        notional
        / window_seconds
    )

    average_trade_size = (
        volume
        / trade_count
    )

    average_trade_notional = (
        notional
        / trade_count
    )

    largest_trade_volume = max(
        trade.quantity
        for trade in trades
    )

    largest_trade_notional = max(
        trade.notional
        for trade in trades
    )

    return TradeIntensityMetrics(
        exchange=exchange,
        symbol=symbol,

        window_seconds=window_seconds,

        trade_count=trade_count,

        volume=volume,
        notional=notional,

        trades_per_second=trades_per_second,
        volume_per_second=volume_per_second,
        notional_per_second=notional_per_second,

        average_trade_size=average_trade_size,
        average_trade_notional=average_trade_notional,

        largest_trade_volume=largest_trade_volume,
        largest_trade_notional=largest_trade_notional,
    )