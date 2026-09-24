from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class MarketTrade:
    """
    Normalized market trade.

    Represents a single executed trade regardless of exchange.
    """

    exchange: str
    symbol: str
    price: float
    quantity: float
    timestamp: datetime
    is_buyer_maker: bool
    trade_id: str | int | None = None

    @property
    def notional(self) -> float:
        return self.price * self.quantity

    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds()

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        return self.age_seconds() <= max_age_seconds


@dataclass(frozen=True)
class OrderBookMetrics:
    """
    Microstructure metrics derived from an order book.
    """

    exchange: str
    symbol: str

    best_bid: float
    best_ask: float

    bid_quantity: float
    ask_quantity: float

    spread: float
    spread_percent: float

    mid_price: float

    bid_notional: float
    ask_notional: float

    imbalance: float
    weighted_imbalance: float

    bid_depth_quantity: float
    ask_depth_quantity: float

    bid_depth_notional: float
    ask_depth_notional: float

    bid_pressure: float
    ask_pressure: float

    weighted_bid_pressure: float
    weighted_ask_pressure: float

    @property
    def total_top_quantity(self) -> float:
        return self.bid_quantity + self.ask_quantity

    @property
    def total_top_notional(self) -> float:
        return self.bid_notional + self.ask_notional

    @property
    def total_depth_quantity(self) -> float:
        return (
            self.bid_depth_quantity
            + self.ask_depth_quantity
        )

    @property
    def total_depth_notional(self) -> float:
        return (
            self.bid_depth_notional
            + self.ask_depth_notional
        )


@dataclass(frozen=True)
class OrderFlowMetrics:
    """
    Trade-flow metrics calculated from executed trades.
    """

    exchange: str
    symbol: str

    trade_count: int

    buy_volume: float
    sell_volume: float

    buy_notional: float
    sell_notional: float

    net_volume: float
    net_notional: float

    buy_ratio: float
    sell_ratio: float


@dataclass(frozen=True)
class MarketMicrostructureSnapshot:
    """
    Combined microstructure state for one exchange
    and one trading pair.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    order_book: OrderBookMetrics
    order_flow: OrderFlowMetrics | None = None

    def age_seconds(self) -> float:
        now = datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds()

    def is_fresh(self, max_age_seconds: float = 5.0) -> bool:
        return self.age_seconds() <= max_age_seconds


def calculate_order_flow_metrics(
    trades: list[MarketTrade],
) -> OrderFlowMetrics:
    """
    Calculate buy/sell order-flow metrics from executed trades.
    """

    if not trades:
        raise ValueError("trades must not be empty")

    exchange = trades[0].exchange
    symbol = trades[0].symbol

    trade_count = len(trades)

    buy_volume = 0.0
    sell_volume = 0.0

    buy_notional = 0.0
    sell_notional = 0.0

    for trade in trades:
        if trade.is_buyer_maker:
            sell_volume += trade.quantity
            sell_notional += trade.notional
        else:
            buy_volume += trade.quantity
            buy_notional += trade.notional

    net_volume = buy_volume - sell_volume
    net_notional = buy_notional - sell_notional

    total_volume = buy_volume + sell_volume

    if total_volume == 0:
        buy_ratio = 0.0
        sell_ratio = 0.0
    else:
        buy_ratio = buy_volume / total_volume
        sell_ratio = sell_volume / total_volume

    return OrderFlowMetrics(
        exchange=exchange,
        symbol=symbol,
        trade_count=trade_count,
        buy_volume=buy_volume,
        sell_volume=sell_volume,
        buy_notional=buy_notional,
        sell_notional=sell_notional,
        net_volume=net_volume,
        net_notional=net_notional,
        buy_ratio=buy_ratio,
        sell_ratio=sell_ratio,
    )


def calculate_weighted_side_quantity(
    levels,
    depth_levels: int,
    decay: float,
) -> float:
    """
    Calculate distance-weighted quantity for one side
    of the order book.
    """

    total = 0.0

    for index, level in enumerate(levels[:depth_levels]):
        weight = 1.0 / ((index + 1) ** decay)
        total += level.quantity * weight

    return total


def calculate_weighted_imbalance(
    order_book: OrderBook,
    depth_levels: int = 5,
    decay: float = 1.0,
) -> float:
    """
    Calculate distance-weighted order book imbalance.

    Levels closer to the best price receive greater weight.

    Result ranges theoretically from -1 to +1.
    """

    if depth_levels <= 0:
        raise ValueError(
            "depth_levels must be greater than zero"
        )

    if decay <= 0:
        raise ValueError(
            "decay must be greater than zero"
        )

    weighted_bid = calculate_weighted_side_quantity(
        order_book.bids,
        depth_levels,
        decay,
    )

    weighted_ask = calculate_weighted_side_quantity(
        order_book.asks,
        depth_levels,
        decay,
    )

    total = weighted_bid + weighted_ask

    if total == 0:
        return 0.0

    return (weighted_bid - weighted_ask) / total


def calculate_order_book_metrics(
    order_book: OrderBook,
    depth_levels: int = 5,
    decay: float = 1.0,
) -> OrderBookMetrics:
    """
    Calculate normalized microstructure metrics
    from an OrderBook.
    """

    if depth_levels <= 0:
        raise ValueError(
            "depth_levels must be greater than zero"
        )

    best_bid = order_book.best_bid
    best_ask = order_book.best_ask

    bid_levels = order_book.bids[:depth_levels]
    ask_levels = order_book.asks[:depth_levels]

    bid_depth_quantity = sum(
        level.quantity
        for level in bid_levels
    )

    ask_depth_quantity = sum(
        level.quantity
        for level in ask_levels
    )

    bid_depth_notional = sum(
        level.price * level.quantity
        for level in bid_levels
    )

    ask_depth_notional = sum(
        level.price * level.quantity
        for level in ask_levels
    )

    total_depth_quantity = (
        bid_depth_quantity
        + ask_depth_quantity
    )

    if total_depth_quantity == 0:
        imbalance = 0.0
    else:
        imbalance = (
            bid_depth_quantity
            - ask_depth_quantity
        ) / total_depth_quantity

    weighted_bid_quantity = calculate_weighted_side_quantity(
        order_book.bids,
        depth_levels,
        decay,
    )

    weighted_ask_quantity = calculate_weighted_side_quantity(
        order_book.asks,
        depth_levels,
        decay,
    )

    weighted_total = (
        weighted_bid_quantity
        + weighted_ask_quantity
    )

    if weighted_total == 0:
        weighted_bid_pressure = 0.0
        weighted_ask_pressure = 0.0
    else:
        weighted_bid_pressure = (
            weighted_bid_quantity
            / weighted_total
        )

        weighted_ask_pressure = (
            weighted_ask_quantity
            / weighted_total
        )

    bid_pressure = (
        bid_depth_quantity
        / total_depth_quantity
        if total_depth_quantity > 0
        else 0.0
    )

    ask_pressure = (
        ask_depth_quantity
        / total_depth_quantity
        if total_depth_quantity > 0
        else 0.0
    )

    weighted_imbalance = calculate_weighted_imbalance(
        order_book=order_book,
        depth_levels=depth_levels,
        decay=decay,
    )

    spread = best_ask.price - best_bid.price

    if best_bid.price <= 0:
        raise ValueError(
            "Best bid price must be greater than zero"
        )

    spread_percent = (
        spread / best_bid.price
    ) * 100

    mid_price = (
        best_bid.price
        + best_ask.price
    ) / 2

    bid_notional = (
        best_bid.price
        * best_bid.quantity
    )

    ask_notional = (
        best_ask.price
        * best_ask.quantity
    )

    return OrderBookMetrics(
        exchange=order_book.exchange,
        symbol=order_book.symbol,

        best_bid=best_bid.price,
        best_ask=best_ask.price,

        bid_quantity=best_bid.quantity,
        ask_quantity=best_ask.quantity,

        spread=spread,
        spread_percent=spread_percent,

        mid_price=mid_price,

        bid_notional=bid_notional,
        ask_notional=ask_notional,

        imbalance=imbalance,
        weighted_imbalance=weighted_imbalance,

        bid_depth_quantity=bid_depth_quantity,
        ask_depth_quantity=ask_depth_quantity,

        bid_depth_notional=bid_depth_notional,
        ask_depth_notional=ask_depth_notional,

        bid_pressure=bid_pressure,
        ask_pressure=ask_pressure,

        weighted_bid_pressure=weighted_bid_pressure,
        weighted_ask_pressure=weighted_ask_pressure,
    )