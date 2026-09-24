from dataclasses import dataclass

from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class LiquidityMetrics:
    """
    Liquidity metrics derived from an order book.
    """

    exchange: str
    symbol: str

    mid_price: float
    spread: float
    spread_percent: float

    bid_depth_quantity: float
    ask_depth_quantity: float

    bid_depth_notional: float
    ask_depth_notional: float

    total_depth_quantity: float
    total_depth_notional: float

    bid_liquidity_ratio: float
    ask_liquidity_ratio: float

    bid_notional_ratio: float
    ask_notional_ratio: float

    bid_concentration: float
    ask_concentration: float


def _safe_ratio(
    numerator: float,
    denominator: float,
) -> float:
    if denominator <= 0:
        return 0.0

    return numerator / denominator


def _depth_metrics(
    order_book: OrderBook,
    depth_levels: int,
) -> tuple[
    float,
    float,
    float,
    float,
]:
    bids = order_book.bids[:depth_levels]
    asks = order_book.asks[:depth_levels]

    bid_depth_quantity = sum(
        level.quantity
        for level in bids
    )

    ask_depth_quantity = sum(
        level.quantity
        for level in asks
    )

    bid_depth_notional = sum(
        level.price * level.quantity
        for level in bids
    )

    ask_depth_notional = sum(
        level.price * level.quantity
        for level in asks
    )

    return (
        bid_depth_quantity,
        ask_depth_quantity,
        bid_depth_notional,
        ask_depth_notional,
    )


def calculate_liquidity_metrics(
    order_book: OrderBook,
    depth_levels: int = 5,
) -> LiquidityMetrics:
    """
    Calculate normalized liquidity metrics from an order book.
    """

    if depth_levels <= 0:
        raise ValueError(
            "depth_levels must be greater than zero"
        )

    best_bid = order_book.best_bid
    best_ask = order_book.best_ask

    mid_price = (
        best_bid.price + best_ask.price
    ) / 2

    spread = (
        best_ask.price - best_bid.price
    )

    if best_bid.price <= 0:
        raise ValueError(
            "best bid price must be greater than zero"
        )

    spread_percent = (
        spread / best_bid.price
    ) * 100

    (
        bid_depth_quantity,
        ask_depth_quantity,
        bid_depth_notional,
        ask_depth_notional,
    ) = _depth_metrics(
        order_book,
        depth_levels,
    )

    total_depth_quantity = (
        bid_depth_quantity
        + ask_depth_quantity
    )

    total_depth_notional = (
        bid_depth_notional
        + ask_depth_notional
    )

    bid_liquidity_ratio = _safe_ratio(
        bid_depth_quantity,
        total_depth_quantity,
    )

    ask_liquidity_ratio = _safe_ratio(
        ask_depth_quantity,
        total_depth_quantity,
    )

    bid_notional_ratio = _safe_ratio(
        bid_depth_notional,
        total_depth_notional,
    )

    ask_notional_ratio = _safe_ratio(
        ask_depth_notional,
        total_depth_notional,
    )

    top_bid_notional = (
        best_bid.price
        * best_bid.quantity
    )

    top_ask_notional = (
        best_ask.price
        * best_ask.quantity
    )

    bid_concentration = _safe_ratio(
        top_bid_notional,
        bid_depth_notional,
    )

    ask_concentration = _safe_ratio(
        top_ask_notional,
        ask_depth_notional,
    )

    return LiquidityMetrics(
        exchange=order_book.exchange,
        symbol=order_book.symbol,
        mid_price=mid_price,
        spread=spread,
        spread_percent=spread_percent,
        bid_depth_quantity=bid_depth_quantity,
        ask_depth_quantity=ask_depth_quantity,
        bid_depth_notional=bid_depth_notional,
        ask_depth_notional=ask_depth_notional,
        total_depth_quantity=total_depth_quantity,
        total_depth_notional=total_depth_notional,
        bid_liquidity_ratio=bid_liquidity_ratio,
        ask_liquidity_ratio=ask_liquidity_ratio,
        bid_notional_ratio=bid_notional_ratio,
        ask_notional_ratio=ask_notional_ratio,
        bid_concentration=bid_concentration,
        ask_concentration=ask_concentration,
    )