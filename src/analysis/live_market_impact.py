from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.market_impact import (
    MarketImpactResult,
    simulate_market_order,
)
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class LiveMarketImpactState:
    """
    Latest live execution-impact state for one market order.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    result: MarketImpactResult

    @property
    def side(self) -> str:
        return self.result.side

    @property
    def requested_quantity(self) -> float:
        return self.result.requested_quantity

    @property
    def filled_quantity(self) -> float:
        return self.result.filled_quantity

    @property
    def unfilled_quantity(self) -> float:
        return self.result.unfilled_quantity

    @property
    def average_execution_price(self) -> float:
        return self.result.average_execution_price

    @property
    def reference_price(self) -> float:
        return self.result.reference_price

    @property
    def slippage(self) -> float:
        return self.result.slippage

    @property
    def slippage_percent(self) -> float:
        return self.result.slippage_percent

    @property
    def price_impact(self) -> float:
        return self.result.price_impact

    @property
    def price_impact_percent(self) -> float:
        return self.result.price_impact_percent

    @property
    def total_notional(self) -> float:
        return self.result.total_notional

    @property
    def levels_consumed(self) -> int:
        return self.result.levels_consumed

    @property
    def fully_filled(self) -> bool:
        return self.result.fully_filled

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


class LiveMarketImpactEngine:
    """
    Calculates market-order impact against the
    latest validated live order book.

    The engine does not place real orders.
    It only estimates execution against visible liquidity.
    """

    def __init__(
        self,
        side: str,
        quantity: float,
    ):
        normalized_side = side.lower().strip()

        if normalized_side not in {
            "buy",
            "sell",
        }:
            raise ValueError(
                "side must be 'buy' or 'sell'"
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be greater than zero"
            )

        self.side = normalized_side
        self.quantity = quantity

        self._latest_state: (
            LiveMarketImpactState | None
        ) = None

        self._update_count = 0

    @property
    def latest_state(
        self,
    ) -> LiveMarketImpactState | None:
        return self._latest_state

    @property
    def update_count(self) -> int:
        return self._update_count

    def update(
        self,
        order_book: OrderBook,
    ) -> LiveMarketImpactState:
        """
        Calculate execution impact using the latest
        validated live order book.
        """

        result = simulate_market_order(
            order_book=order_book,
            side=self.side,
            quantity=self.quantity,
        )

        state = LiveMarketImpactState(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            timestamp=order_book.received_at,
            result=result,
        )

        self._latest_state = state
        self._update_count += 1

        return state

    def set_order(
        self,
        side: str,
        quantity: float,
    ) -> None:
        """
        Change the simulated order parameters.
        """

        normalized_side = side.lower().strip()

        if normalized_side not in {
            "buy",
            "sell",
        }:
            raise ValueError(
                "side must be 'buy' or 'sell'"
            )

        if quantity <= 0:
            raise ValueError(
                "quantity must be greater than zero"
            )

        self.side = normalized_side
        self.quantity = quantity

    def reset(self) -> None:
        """
        Clear the latest live impact state.
        """

        self._latest_state = None
        self._update_count = 0