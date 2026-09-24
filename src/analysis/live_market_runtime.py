import threading
from typing import Callable

from src.analysis.live_market_state import (
    LiveMarketState,
    LiveMarketStateEngine,
)
from src.analysis.live_microstructure import (
    LiveMicrostructureEngine,
)
from src.analysis.live_order_flow import (
    LiveOrderFlowEngine,
)
from src.exchanges.binance_orderbook_sync import (
    BinanceOrderBookSync,
)
from src.exchanges.binance_ws import (
    BinanceTradeWebSocket,
)


class LiveMarketRuntime:
    """
    Coordinates Binance order-book synchronization,
    live trades, microstructure analysis, order flow,
    and the combined live market state.
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        snapshot_limit: int = 100,
        microstructure_depth_levels: int = 5,
        microstructure_decay: float = 1.0,
    ):
        self.symbol = symbol

        self._microstructure_engine = (
            LiveMicrostructureEngine(
                depth_levels=microstructure_depth_levels,
                decay=microstructure_decay,
            )
        )

        self._order_flow_engine = LiveOrderFlowEngine(
            exchange="binance",
            symbol=symbol,
        )

        self._market_state_engine = (
            LiveMarketStateEngine()
        )

        self._order_book_sync = (
            BinanceOrderBookSync(
                symbol=symbol,
                snapshot_limit=snapshot_limit,
                microstructure_depth_levels=(
                    microstructure_depth_levels
                ),
                microstructure_decay=(
                    microstructure_decay
                ),
            )
        )

        self._trade_stream = BinanceTradeWebSocket(
            symbol=symbol,
        )

        self._on_market_state: (
            Callable[[LiveMarketState], None]
            | None
        ) = None

        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return (
            self._order_book_sync.is_running
            or self._trade_stream.is_running
        )

    @property
    def is_synchronized(self) -> bool:
        return self._order_book_sync.is_synchronized

    @property
    def latest_state(self) -> LiveMarketState | None:
        return self._market_state_engine.latest_state

    @property
    def market_state_update_count(self) -> int:
        return self._market_state_engine.update_count

    @property
    def order_book_update_count(self) -> int:
        return (
            self._order_book_sync.microstructure_update_count
        )

    @property
    def trade_count(self) -> int:
        return self._order_flow_engine.trade_count

    @property
    def cvd(self) -> float:
        return self._order_flow_engine.cvd

    @property
    def received_trade_count(self) -> int:
        return self._trade_stream.received_count

    @property
    def trade_error_count(self) -> int:
        return self._trade_stream.error_count

    @property
    def order_book_received_events(self) -> int:
        return self._order_book_sync.received_events

    @property
    def order_book_applied_events(self) -> int:
        return self._order_book_sync.applied_events

    @property
    def order_book_gap_count(self) -> int:
        return self._order_book_sync.gap_count

    @property
    def order_book_resync_count(self) -> int:
        return self._order_book_sync.resync_count

    @property
    def order_book_error_count(self) -> int:
        return self._order_book_sync.error_count

    def _publish_market_state(
        self,
        state: LiveMarketState | None,
    ) -> None:
        if state is None:
            return

        callback = self._on_market_state

        if callback is not None:
            callback(state)

    def _handle_microstructure(
        self,
        state,
    ) -> None:
        combined_state = (
            self._market_state_engine
            .update_microstructure(state)
        )

        self._publish_market_state(
            combined_state,
        )

    def _handle_trade(
        self,
        trade,
    ) -> None:
        order_flow_state = (
            self._order_flow_engine.update(
                trade,
            )
        )

        combined_state = (
            self._market_state_engine
            .update_order_flow(
                order_flow_state,
            )
        )

        self._publish_market_state(
            combined_state,
        )

    def start(
        self,
        on_market_state: (
            Callable[[LiveMarketState], None]
            | None
        ) = None,
    ) -> None:
        if self.is_running:
            raise RuntimeError(
                "Live market runtime is already running"
            )

        self._on_market_state = on_market_state

        self._microstructure_engine.reset()
        self._order_flow_engine.reset()
        self._market_state_engine.reset()

        self._order_book_sync.start(
            on_microstructure=self._handle_microstructure,
        )

        self._trade_stream.start(
            on_trade=self._handle_trade,
        )

    def stop(self) -> None:
        self._trade_stream.stop()
        self._order_book_sync.stop()

        self._on_market_state = None

    def get_state(self) -> LiveMarketState:
        state = self.latest_state

        if state is None:
            raise RuntimeError(
                "Live market state is not available"
            )

        return state