from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.live_microstructure import (
    LiveMicrostructureState,
)
from src.analysis.live_order_flow import (
    LiveOrderFlowState,
)


@dataclass(frozen=True)
class LiveMarketState:
    """
    Combined live market state.

    Combines order-book microstructure and
    executed-trade order flow into one state.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    microstructure: LiveMicrostructureState
    order_flow: LiveOrderFlowState

    @property
    def best_bid(self) -> float:
        return self.microstructure.best_bid

    @property
    def best_ask(self) -> float:
        return self.microstructure.best_ask

    @property
    def mid_price(self) -> float:
        return self.microstructure.mid_price

    @property
    def spread(self) -> float:
        return self.microstructure.spread

    @property
    def spread_percent(self) -> float:
        return self.microstructure.spread_percent

    @property
    def imbalance(self) -> float:
        return self.microstructure.imbalance

    @property
    def weighted_imbalance(self) -> float:
        return self.microstructure.weighted_imbalance

    @property
    def trade_count(self) -> int:
        return self.order_flow.trade_count

    @property
    def buy_volume(self) -> float:
        return self.order_flow.buy_volume

    @property
    def sell_volume(self) -> float:
        return self.order_flow.sell_volume

    @property
    def net_volume(self) -> float:
        return self.order_flow.net_volume

    @property
    def net_notional(self) -> float:
        return self.order_flow.net_notional

    @property
    def buy_ratio(self) -> float:
        return self.order_flow.buy_ratio

    @property
    def sell_ratio(self) -> float:
        return self.order_flow.sell_ratio

    @property
    def cvd(self) -> float:
        return self.order_flow.cvd

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


class LiveMarketStateEngine:
    """
    Combines live microstructure and order-flow states.

    The engine keeps the latest state from each component
    and publishes a combined LiveMarketState whenever
    both components are available.
    """

    def __init__(self):
        self._latest_microstructure: (
            LiveMicrostructureState | None
        ) = None

        self._latest_order_flow: (
            LiveOrderFlowState | None
        ) = None

        self._latest_state: (
            LiveMarketState | None
        ) = None

        self._update_count = 0

    @property
    def latest_state(
        self,
    ) -> LiveMarketState | None:
        return self._latest_state

    @property
    def latest_microstructure(
        self,
    ) -> LiveMicrostructureState | None:
        return self._latest_microstructure

    @property
    def latest_order_flow(
        self,
    ) -> LiveOrderFlowState | None:
        return self._latest_order_flow

    @property
    def update_count(self) -> int:
        return self._update_count

    def update_microstructure(
        self,
        state: LiveMicrostructureState,
    ) -> LiveMarketState | None:
        self._latest_microstructure = state

        return self._build_state()

    def update_order_flow(
        self,
        state: LiveOrderFlowState,
    ) -> LiveMarketState | None:
        self._latest_order_flow = state

        return self._build_state()

    def _build_state(
        self,
    ) -> LiveMarketState | None:
        if (
            self._latest_microstructure is None
            or self._latest_order_flow is None
        ):
            return None

        microstructure = self._latest_microstructure
        order_flow = self._latest_order_flow

        if microstructure.exchange != order_flow.exchange:
            raise ValueError(
                "microstructure and order flow exchanges do not match"
            )

        if microstructure.symbol != order_flow.symbol:
            raise ValueError(
                "microstructure and order flow symbols do not match"
            )

        timestamp = max(
            microstructure.timestamp,
            order_flow.timestamp,
        )

        state = LiveMarketState(
            exchange=microstructure.exchange,
            symbol=microstructure.symbol,
            timestamp=timestamp,
            microstructure=microstructure,
            order_flow=order_flow,
        )

        self._latest_state = state
        self._update_count += 1

        return state

    def reset(self) -> None:
        self._latest_microstructure = None
        self._latest_order_flow = None
        self._latest_state = None
        self._update_count = 0