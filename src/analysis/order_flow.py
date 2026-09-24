from dataclasses import dataclass
from datetime import datetime

from src.analysis.microstructure import MarketTrade


@dataclass(frozen=True)
class TradeFlowEvent:
    """
    Normalized event generated from an executed market trade.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    price: float
    quantity: float
    notional: float

    side: str

    delta_volume: float
    delta_notional: float

    is_large_trade: bool


@dataclass(frozen=True)
class TradeFlowState:
    """
    Aggregated state of market order flow.
    """

    exchange: str
    symbol: str

    trade_count: int

    buy_volume: float
    sell_volume: float

    net_volume: float

    buy_notional: float
    sell_notional: float

    net_notional: float

    buy_ratio: float
    sell_ratio: float

    large_trade_count: int
    large_trade_volume: float

    cvd: float


def classify_trade(
    trade: MarketTrade,
) -> str:
    """
    Classify an executed trade by aggressor side.

    buyer_maker=True means the buyer was the passive maker,
    therefore the aggressive side was the seller.

    buyer_maker=False means the aggressive side was the buyer.
    """

    if trade.is_buyer_maker:
        return "sell"

    return "buy"


def create_trade_flow_event(
    trade: MarketTrade,
    large_trade_threshold: float = 100_000.0,
) -> TradeFlowEvent:
    """
    Convert a normalized MarketTrade into a TradeFlowEvent.
    """

    if large_trade_threshold <= 0:
        raise ValueError(
            "large_trade_threshold must be greater than zero"
        )

    side = classify_trade(trade)

    notional = trade.notional

    if side == "buy":
        delta_volume = trade.quantity
        delta_notional = notional
    else:
        delta_volume = -trade.quantity
        delta_notional = -notional

    is_large_trade = (
        notional >= large_trade_threshold
    )

    return TradeFlowEvent(
        exchange=trade.exchange,
        symbol=trade.symbol,
        timestamp=trade.timestamp,

        price=trade.price,
        quantity=trade.quantity,
        notional=notional,

        side=side,

        delta_volume=delta_volume,
        delta_notional=delta_notional,

        is_large_trade=is_large_trade,
    )


def build_trade_flow_state(
    trades: list[MarketTrade],
    large_trade_threshold: float = 100_000.0,
) -> TradeFlowState:
    """
    Build an aggregated trade-flow state from executed trades.
    """

    if not trades:
        raise ValueError(
            "trades must not be empty"
        )

    events = [
        create_trade_flow_event(
            trade,
            large_trade_threshold=large_trade_threshold,
        )
        for trade in trades
    ]

    exchange = events[0].exchange
    symbol = events[0].symbol

    buy_volume = sum(
        event.quantity
        for event in events
        if event.side == "buy"
    )

    sell_volume = sum(
        event.quantity
        for event in events
        if event.side == "sell"
    )

    buy_notional = sum(
        event.notional
        for event in events
        if event.side == "buy"
    )

    sell_notional = sum(
        event.notional
        for event in events
        if event.side == "sell"
    )

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

    large_trade_events = [
        event
        for event in events
        if event.is_large_trade
    ]

    large_trade_count = len(
        large_trade_events
    )

    large_trade_volume = sum(
        event.quantity
        for event in large_trade_events
    )

    cvd = sum(
        event.delta_volume
        for event in events
    )

    return TradeFlowState(
        exchange=exchange,
        symbol=symbol,

        trade_count=len(events),

        buy_volume=buy_volume,
        sell_volume=sell_volume,

        net_volume=net_volume,

        buy_notional=buy_notional,
        sell_notional=sell_notional,

        net_notional=net_notional,

        buy_ratio=buy_ratio,
        sell_ratio=sell_ratio,

        large_trade_count=large_trade_count,
        large_trade_volume=large_trade_volume,

        cvd=cvd,
    )