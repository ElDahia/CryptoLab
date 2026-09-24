from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from src.analysis.live_market_impact_monitor import (
    LiveMarketImpactMonitor,
    LiveMarketImpactMonitorState,
)
from src.analysis.live_liquidity import (
    LiveLiquidityEngine,
    LiveLiquidityState,
)
from src.analysis.live_microstructure import (
    LiveMicrostructureEngine,
    LiveMicrostructureState,
)
from src.analysis.live_order_flow import (
    LiveOrderFlowEngine,
    LiveOrderFlowState,
)
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class LiveExecutionIntelligenceState:
    """
    Combined execution-intelligence state.

    Combines live market microstructure, order flow,
    liquidity, and market-impact analysis.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    microstructure: LiveMicrostructureState
    order_flow: LiveOrderFlowState
    liquidity: LiveLiquidityState
    market_impact: LiveMarketImpactMonitorState

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
    def cvd(self) -> float:
        return self.order_flow.cvd

    @property
    def total_depth_notional(self) -> float:
        return self.liquidity.total_depth_notional

    @property
    def bid_depth_notional(self) -> float:
        return self.liquidity.bid_depth_notional

    @property
    def ask_depth_notional(self) -> float:
        return self.liquidity.ask_depth_notional

    @property
    def buy_price_impact_percent(self) -> float:
        return self.market_impact.buy_price_impact_percent

    @property
    def sell_price_impact_percent(self) -> float:
        return self.market_impact.sell_price_impact_percent

    @property
    def buy_slippage_percent(self) -> float:
        return self.market_impact.buy_slippage_percent

    @property
    def sell_slippage_percent(self) -> float:
        return self.market_impact.sell_slippage_percent

    @property
    def buy_levels_consumed(self) -> int:
        return self.market_impact.buy_levels_consumed

    @property
    def sell_levels_consumed(self) -> int:
        return self.market_impact.sell_levels_consumed

    @property
    def buy_fully_filled(self) -> bool:
        return self.market_impact.buy_fully_filled

    @property
    def sell_fully_filled(self) -> bool:
        return self.market_impact.sell_fully_filled

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


class LiveExecutionIntelligenceEngine:
    """
    Combines live validated order-book data with
    microstructure, order flow, liquidity, and
    market-impact analysis.

    This engine performs analysis only.
    It does not place real orders.
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        microstructure_depth_levels: int = 5,
        microstructure_decay: float = 1.0,
        liquidity_depth_levels: int = 5,
        buy_quantity: float = 10.0,
        sell_quantity: float = 10.0,
        profile_distances_bps: tuple[float, ...] = (
            1.0,
            2.0,
            5.0,
            10.0,
            25.0,
            50.0,
            100.0,
        ),
    ):
        self.symbol = symbol

        self.microstructure_engine = (
            LiveMicrostructureEngine(
                depth_levels=microstructure_depth_levels,
                decay=microstructure_decay,
            )
        )

        self.order_flow_engine = LiveOrderFlowEngine(
            exchange="binance",
            symbol=symbol,
        )

        self.liquidity_engine = LiveLiquidityEngine(
            depth_levels=liquidity_depth_levels,
            profile_distances_bps=profile_distances_bps,
        )

        self.market_impact_monitor = (
            LiveMarketImpactMonitor(
                buy_quantity=buy_quantity,
                sell_quantity=sell_quantity,
            )
        )

        self._latest_state: (
            LiveExecutionIntelligenceState | None
        ) = None

        self._update_count = 0

        self._on_update: (
            Callable[
                [LiveExecutionIntelligenceState],
                None,
            ]
            | None
        ) = None

    @property
    def latest_state(
        self,
    ) -> LiveExecutionIntelligenceState | None:
        return self._latest_state

    @property
    def update_count(self) -> int:
        return self._update_count

    def set_callback(
        self,
        callback: (
            Callable[
                [LiveExecutionIntelligenceState],
                None,
            ]
            | None
        ),
    ) -> None:
        self._on_update = callback

    def update_order_book(
        self,
        order_book: OrderBook,
    ) -> LiveExecutionIntelligenceState:
        """
        Update all order-book-based intelligence engines
        from one validated live order book.
        """

        microstructure = (
            self.microstructure_engine.update(
                order_book
            )
        )

        liquidity = self.liquidity_engine.update(
            order_book
        )

        market_impact = (
            self.market_impact_monitor.update(
                order_book
            )
        )

        existing_order_flow = (
            self.order_flow_engine.latest_state
        )

        if existing_order_flow is None:
            raise RuntimeError(
                "Order flow state is not available yet"
            )

        state = LiveExecutionIntelligenceState(
            exchange=order_book.exchange,
            symbol=order_book.symbol,
            timestamp=max(
                microstructure.timestamp,
                existing_order_flow.timestamp,
                liquidity.timestamp,
                market_impact.timestamp,
            ),
            microstructure=microstructure,
            order_flow=existing_order_flow,
            liquidity=liquidity,
            market_impact=market_impact,
        )

        self._latest_state = state
        self._update_count += 1

        if self._on_update is not None:
            self._on_update(state)

        return state

    def update_trade(
        self,
        trade,
    ) -> LiveExecutionIntelligenceState | None:
        """
        Update order flow from one live trade.

        A combined state is published only when
        a validated order-book state already exists.
        """

        order_flow = self.order_flow_engine.update(
            trade
        )

        if self._latest_state is None:
            return None

        previous = self._latest_state

        state = LiveExecutionIntelligenceState(
            exchange=trade.exchange,
            symbol=trade.symbol,
            timestamp=max(
                previous.microstructure.timestamp,
                order_flow.timestamp,
                previous.liquidity.timestamp,
                previous.market_impact.timestamp,
            ),
            microstructure=previous.microstructure,
            order_flow=order_flow,
            liquidity=previous.liquidity,
            market_impact=previous.market_impact,
        )

        self._latest_state = state
        self._update_count += 1

        if self._on_update is not None:
            self._on_update(state)

        return state

    def set_impact_quantities(
        self,
        buy_quantity: float,
        sell_quantity: float,
    ) -> None:
        """
        Change the monitored execution quantities.
        """

        self.market_impact_monitor.set_quantities(
            buy_quantity=buy_quantity,
            sell_quantity=sell_quantity,
        )

    def reset(self) -> None:
        """
        Reset all intelligence engines.
        """

        self.microstructure_engine.reset()
        self.order_flow_engine.reset()
        self.liquidity_engine.reset()
        self.market_impact_monitor.reset()

        self._latest_state = None
        self._update_count = 0