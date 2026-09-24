from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from src.analysis.live_market_impact import (
    LiveMarketImpactEngine,
    LiveMarketImpactState,
)
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class LiveMarketImpactMonitorState:
    """
    Latest monitored market-impact state.

    Contains the latest impact estimates for both
    buy and sell execution against the validated
    live order book.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    buy: LiveMarketImpactState
    sell: LiveMarketImpactState

    @property
    def buy_slippage(self) -> float:
        return self.buy.slippage

    @property
    def sell_slippage(self) -> float:
        return self.sell.slippage

    @property
    def buy_slippage_percent(self) -> float:
        return self.buy.slippage_percent

    @property
    def sell_slippage_percent(self) -> float:
        return self.sell.slippage_percent

    @property
    def buy_price_impact_percent(self) -> float:
        return self.buy.price_impact_percent

    @property
    def sell_price_impact_percent(self) -> float:
        return self.sell.price_impact_percent

    @property
    def buy_average_execution_price(self) -> float:
        return self.buy.average_execution_price

    @property
    def sell_average_execution_price(self) -> float:
        return self.sell.average_execution_price

    @property
    def buy_levels_consumed(self) -> int:
        return self.buy.levels_consumed

    @property
    def sell_levels_consumed(self) -> int:
        return self.sell.levels_consumed

    @property
    def buy_fully_filled(self) -> bool:
        return self.buy.fully_filled

    @property
    def sell_fully_filled(self) -> bool:
        return self.sell.fully_filled

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


class LiveMarketImpactMonitor:
    """
    Continuously evaluates the execution impact of
    predefined buy and sell quantities against the
    latest validated live order book.

    This component does not place real orders.
    It only measures visible market impact.
    """

    def __init__(
        self,
        buy_quantity: float = 10.0,
        sell_quantity: float = 10.0,
    ):
        if buy_quantity <= 0:
            raise ValueError(
                "buy_quantity must be greater than zero"
            )

        if sell_quantity <= 0:
            raise ValueError(
                "sell_quantity must be greater than zero"
            )

        self.buy_engine = LiveMarketImpactEngine(
            side="buy",
            quantity=buy_quantity,
        )

        self.sell_engine = LiveMarketImpactEngine(
            side="sell",
            quantity=sell_quantity,
        )

        self._latest_state: (
            LiveMarketImpactMonitorState | None
        ) = None

        self._update_count = 0

        self._on_update: (
            Callable[
                [LiveMarketImpactMonitorState],
                None,
            ]
            | None
        ) = None

    @property
    def latest_state(
        self,
    ) -> LiveMarketImpactMonitorState | None:
        return self._latest_state

    @property
    def update_count(self) -> int:
        return self._update_count

    @property
    def buy_quantity(self) -> float:
        return self.buy_engine.quantity

    @property
    def sell_quantity(self) -> float:
        return self.sell_engine.quantity

    def set_callback(
        self,
        callback: (
            Callable[
                [LiveMarketImpactMonitorState],
                None,
            ]
            | None
        ),
    ) -> None:
        self._on_update = callback

    def update(
        self,
        order_book: OrderBook,
    ) -> LiveMarketImpactMonitorState:
        """
        Recalculate buy and sell market impact using
        the latest validated order book.
        """

        buy_state = self.buy_engine.update(
            order_book
        )

        sell_state = self.sell_engine.update(
            order_book
        )

        timestamp = max(
            buy_state.timestamp,
            sell_state.timestamp,
        )

        state = LiveMarketImpactMonitorState(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            timestamp=timestamp,
            buy=buy_state,
            sell=sell_state,
        )

        self._latest_state = state
        self._update_count += 1

        if self._on_update is not None:
            self._on_update(state)

        return state

    def set_quantities(
        self,
        buy_quantity: float,
        sell_quantity: float,
    ) -> None:
        """
        Change the monitored buy and sell quantities.
        """

        self.buy_engine.set_order(
            side="buy",
            quantity=buy_quantity,
        )

        self.sell_engine.set_order(
            side="sell",
            quantity=sell_quantity,
        )

    def reset(self) -> None:
        """
        Clear the latest monitor state.
        """

        self.buy_engine.reset()
        self.sell_engine.reset()

        self._latest_state = None
        self._update_count = 0