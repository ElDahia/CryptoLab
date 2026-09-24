from dataclasses import dataclass

from src.exchanges.models import OrderBook


EPSILON = 1e-12


@dataclass(frozen=True)
class ExecutionLevel:
    """
    One order-book level consumed by a simulated market order.
    """

    price: float
    quantity: float
    filled_quantity: float
    notional: float


@dataclass(frozen=True)
class MarketImpactResult:
    """
    Estimated execution impact for a market order.
    """

    side: str
    requested_quantity: float
    filled_quantity: float

    average_execution_price: float
    reference_price: float

    slippage: float
    slippage_percent: float

    price_impact: float
    price_impact_percent: float

    total_notional: float
    levels_consumed: int

    fully_filled: bool
    execution_levels: tuple[ExecutionLevel, ...]

    @property
    def unfilled_quantity(self) -> float:
        remaining = (
            self.requested_quantity
            - self.filled_quantity
        )

        if abs(remaining) <= EPSILON:
            return 0.0

        return max(remaining, 0.0)


def _validate_side(side: str) -> str:
    normalized = side.lower().strip()

    if normalized not in {"buy", "sell"}:
        raise ValueError(
            "side must be 'buy' or 'sell'"
        )

    return normalized


def simulate_market_order(
    order_book: OrderBook,
    side: str,
    quantity: float,
) -> MarketImpactResult:
    """
    Simulate consuming the visible order book
    with a market buy or market sell.

    Buy orders consume asks.
    Sell orders consume bids.
    """

    side = _validate_side(side)

    if quantity <= 0:
        raise ValueError(
            "quantity must be greater than zero"
        )

    best_bid = order_book.best_bid
    best_ask = order_book.best_ask

    if side == "buy":
        levels = order_book.asks
        reference_price = best_ask.price
    else:
        levels = order_book.bids
        reference_price = best_bid.price

    remaining_quantity = quantity
    filled_quantity = 0.0
    total_notional = 0.0

    execution_levels = []

    for level in levels:

        if remaining_quantity <= EPSILON:
            break

        fill_quantity = min(
            remaining_quantity,
            level.quantity,
        )

        if fill_quantity <= 0:
            continue

        notional = (
            level.price
            * fill_quantity
        )

        execution_levels.append(
            ExecutionLevel(
                price=level.price,
                quantity=level.quantity,
                filled_quantity=fill_quantity,
                notional=notional,
            )
        )

        filled_quantity += fill_quantity
        total_notional += notional
        remaining_quantity -= fill_quantity

    if filled_quantity <= 0:
        raise RuntimeError(
            "No liquidity available for execution"
        )

    if abs(
        filled_quantity - quantity
    ) <= EPSILON:
        filled_quantity = quantity

    average_execution_price = (
        total_notional
        / filled_quantity
    )

    if side == "buy":
        slippage = (
            average_execution_price
            - reference_price
        )
    else:
        slippage = (
            reference_price
            - average_execution_price
        )

    if abs(slippage) <= EPSILON:
        slippage = 0.0

    slippage_percent = (
        slippage
        / reference_price
    ) * 100

    price_impact = abs(slippage)

    price_impact_percent = (
        price_impact
        / reference_price
    ) * 100

    fully_filled = (
        filled_quantity >= quantity
        or abs(
            filled_quantity - quantity
        ) <= EPSILON
    )

    return MarketImpactResult(
        side=side,
        requested_quantity=quantity,
        filled_quantity=filled_quantity,
        average_execution_price=average_execution_price,
        reference_price=reference_price,
        slippage=slippage,
        slippage_percent=slippage_percent,
        price_impact=price_impact,
        price_impact_percent=price_impact_percent,
        total_notional=total_notional,
        levels_consumed=len(execution_levels),
        fully_filled=fully_filled,
        execution_levels=tuple(
            execution_levels
        ),
    )