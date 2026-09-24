from dataclasses import dataclass

from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class LiquidityBand:
    """
    Liquidity available inside a price-distance band.
    """

    distance_bps: float

    bid_quantity: float
    ask_quantity: float

    bid_notional: float
    ask_notional: float

    @property
    def total_quantity(self) -> float:
        return self.bid_quantity + self.ask_quantity

    @property
    def total_notional(self) -> float:
        return self.bid_notional + self.ask_notional

    @property
    def bid_ratio(self) -> float:
        if self.total_quantity <= 0:
            return 0.0
        return self.bid_quantity / self.total_quantity

    @property
    def ask_ratio(self) -> float:
        if self.total_quantity <= 0:
            return 0.0
        return self.ask_quantity / self.total_quantity


@dataclass(frozen=True)
class LiquidityProfile:
    """
    Distance-based liquidity profile for an order book.
    """

    exchange: str
    symbol: str
    mid_price: float

    bands: tuple[LiquidityBand, ...]

    @property
    def total_bid_quantity(self) -> float:
        if not self.bands:
            return 0.0

        return self.bands[-1].bid_quantity

    @property
    def total_ask_quantity(self) -> float:
        if not self.bands:
            return 0.0

        return self.bands[-1].ask_quantity

    @property
    def total_bid_notional(self) -> float:
        if not self.bands:
            return 0.0

        return self.bands[-1].bid_notional

    @property
    def total_ask_notional(self) -> float:
        if not self.bands:
            return 0.0

        return self.bands[-1].ask_notional


def _distance_bps(
    price: float,
    mid_price: float,
) -> float:
    """
    Calculate absolute price distance from mid
    in basis points.
    """

    if mid_price <= 0:
        raise ValueError(
            "mid_price must be greater than zero"
        )

    return (
        abs(price - mid_price)
        / mid_price
    ) * 10_000


def calculate_liquidity_profile(
    order_book: OrderBook,
    distances_bps: tuple[float, ...] = (
        1.0,
        2.0,
        5.0,
        10.0,
        25.0,
        50.0,
        100.0,
    ),
) -> LiquidityProfile:
    """
    Calculate cumulative liquidity at multiple
    distances from the order-book mid price.

    Each band contains all liquidity available
    within that distance from the mid price.
    """

    if not distances_bps:
        raise ValueError(
            "distances_bps must not be empty"
        )

    normalized_distances = tuple(
        float(distance)
        for distance in distances_bps
    )

    if any(
        distance <= 0
        for distance in normalized_distances
    ):
        raise ValueError(
            "all distances_bps must be greater than zero"
        )

    if any(
        normalized_distances[index]
        >= normalized_distances[index + 1]
        for index in range(
            len(normalized_distances) - 1
        )
    ):
        raise ValueError(
            "distances_bps must be strictly increasing"
        )

    best_bid = order_book.best_bid
    best_ask = order_book.best_ask

    mid_price = (
        best_bid.price + best_ask.price
    ) / 2

    bands = []

    for distance_bps in normalized_distances:
        bid_quantity = 0.0
        ask_quantity = 0.0

        bid_notional = 0.0
        ask_notional = 0.0

        for level in order_book.bids:
            distance = _distance_bps(
                level.price,
                mid_price,
            )

            if distance <= distance_bps:
                bid_quantity += level.quantity
                bid_notional += (
                    level.price * level.quantity
                )

        for level in order_book.asks:
            distance = _distance_bps(
                level.price,
                mid_price,
            )

            if distance <= distance_bps:
                ask_quantity += level.quantity
                ask_notional += (
                    level.price * level.quantity
                )

        bands.append(
            LiquidityBand(
                distance_bps=distance_bps,
                bid_quantity=bid_quantity,
                ask_quantity=ask_quantity,
                bid_notional=bid_notional,
                ask_notional=ask_notional,
            )
        )

    return LiquidityProfile(
        exchange=order_book.exchange,
        symbol=order_book.symbol,
        mid_price=mid_price,
        bands=tuple(bands),
    )