from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.analysis.adaptive_execution_engine_v5 import AdaptiveExecutionEngineV5
from src.analysis.execution_decision import (
    ExecutionDecision,
    ExecutionDecisionEngine,
)
from src.analysis.live_execution_intelligence import (
    LiveExecutionIntelligenceEngine,
    LiveExecutionIntelligenceState,
)
from src.analysis.risk_engine import RiskAssessment, RiskEngine
from src.analysis.v6_execution_simulation import V6ExecutionSimulation
from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.analysis.v6_market_state import (
    V6MarketState,
    V6MarketStateMonitor,
)
from src.exchanges.binance_ws import BinanceTradeWebSocket
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class V6ExecutionEngineResult:
    """
    Complete V6 execution-analysis result.

    Simulation only.
    No real exchange orders are submitted.
    """

    market_state: V6MarketState
    intelligence_state: LiveExecutionIntelligenceState
    decision: ExecutionDecision
    risk_assessment: RiskAssessment
    simulation_result: object


class V6ExecutionEngine:
    """
    V6 live execution intelligence and simulation pipeline.

    Live data sources:

        Binance L2 Order Book
                ↓
        Market State
                ↓
        Microstructure
        Liquidity
        Market Impact
                ↓
        Execution Intelligence
                ↑
        Binance Live Trades
                ↓
        Order Flow / CVD
                ↓
        Execution Decision
                ↓
        Risk Engine
                ↓
        Adaptive Execution V5
                ↓
        V6 Execution Simulation

    No real orders are submitted.
    """

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        requested_quantity: float = 2.0,
        snapshot_limit: int = 1000,
        decision_engine: Optional[ExecutionDecisionEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        adaptive_engine: Optional[AdaptiveExecutionEngineV5] = None,
    ):
        self.symbol = symbol
        self.requested_quantity = requested_quantity

        # ---------------------------------------------------------
        # Live L2 order-book feed
        # ---------------------------------------------------------
        self.feed = V6LiveMarketFeed(
            symbol=symbol,
            snapshot_limit=snapshot_limit,
        )

        # ---------------------------------------------------------
        # Market-state monitor
        # ---------------------------------------------------------
        self.market_state_monitor = V6MarketStateMonitor()

        # ---------------------------------------------------------
        # Live execution intelligence
        # ---------------------------------------------------------
        self.intelligence_engine = LiveExecutionIntelligenceEngine(
            symbol=symbol,
            buy_quantity=requested_quantity,
            sell_quantity=requested_quantity,
        )

        # ---------------------------------------------------------
        # Live Binance executed-trade feed
        #
        # IMPORTANT:
        # BinanceTradeWebSocket accepts the callback through
        # start(on_trade=...), not through __init__().
        # ---------------------------------------------------------
        self.trade_feed = BinanceTradeWebSocket(
            symbol=symbol,
        )

        # ---------------------------------------------------------
        # Decision engine
        # ---------------------------------------------------------
        self.decision_engine = (
            decision_engine
            if decision_engine is not None
            else ExecutionDecisionEngine()
        )

        # ---------------------------------------------------------
        # Risk engine
        # ---------------------------------------------------------
        self.risk_engine = (
            risk_engine
            if risk_engine is not None
            else RiskEngine()
        )

        # ---------------------------------------------------------
        # Simulation layer
        # ---------------------------------------------------------
        self.simulation = V6ExecutionSimulation(
            feed=self.feed,
            engine=adaptive_engine,
        )

        self._latest_result: Optional[V6ExecutionEngineResult] = None

        self._trade_callback_error_count = 0

    # =============================================================
    # STATUS
    # =============================================================

    @property
    def is_running(self) -> bool:
        return (
            self.feed.is_running
            and self.trade_feed.is_running
        )

    @property
    def order_book_running(self) -> bool:
        return self.feed.is_running

    @property
    def trade_feed_running(self) -> bool:
        return self.trade_feed.is_running

    @property
    def latest_result(
        self,
    ) -> Optional[V6ExecutionEngineResult]:
        return self._latest_result

    @property
    def trade_count(self) -> int:
        return self.trade_feed.received_count

    @property
    def processed_trade_count(self) -> int:
        return self.trade_feed.processed_count

    @property
    def trade_error_count(self) -> int:
        return self.trade_feed.error_count

    @property
    def trade_callback_error_count(self) -> int:
        return self._trade_callback_error_count

    # =============================================================
    # LIVE TRADE CALLBACK
    # =============================================================

    def _on_trade(self, trade) -> None:
        """
        Receive normalized MarketTrade objects from Binance and
        update the execution-intelligence order-flow engine.
        """

        try:
            self.intelligence_engine.update_trade(
                trade
            )

        except Exception:
            self._trade_callback_error_count += 1

    # =============================================================
    # START
    # =============================================================

    def start(self) -> None:
        """
        Start both live market-data sources.

        Order book:
            Binance L2 depth stream

        Trades:
            Binance executed-trade stream
        """

        if (
            self.feed.is_running
            or self.trade_feed.is_running
        ):
            raise RuntimeError(
                "V6 execution engine is already running"
            )

        # Start L2 order-book feed.
        self.feed.start()

        # Start executed-trade feed and attach callback.
        self.trade_feed.start(
            on_trade=self._on_trade,
        )

    # =============================================================
    # STOP
    # =============================================================

    def stop(self) -> None:
        """
        Stop both live market-data sources.
        """

        self.trade_feed.stop()
        self.feed.stop()

    # =============================================================
    # PROCESS LATEST
    # =============================================================

    def process_latest(
        self,
    ) -> V6ExecutionEngineResult:
        """
        Process the latest validated live order book.

        Requires:

        1. L2 feed running
        2. Trade feed running
        3. L2 feed synchronized
        4. At least one live trade received
        """

        if not self.feed.is_running:
            raise RuntimeError(
                "V6 execution engine order-book feed "
                "is not running"
            )

        if not self.trade_feed.is_running:
            raise RuntimeError(
                "V6 execution engine trade feed "
                "is not running"
            )

        if not self.feed.is_synchronized:
            raise RuntimeError(
                "Live market feed is not synchronized"
            )

        if self.trade_count <= 0:
            raise RuntimeError(
                "No live trades received yet"
            )

        order_book = (
            self.feed.get_latest_order_book()
        )

        if order_book is None:
            raise RuntimeError(
                "No validated live order book available"
            )

        return self.process_order_book(
            order_book
        )

    # =============================================================
    # PROCESS ORDER BOOK
    # =============================================================

    def process_order_book(
        self,
        order_book: OrderBook,
    ) -> V6ExecutionEngineResult:
        """
        Run the complete:

        Market State
            ↓
        Execution Intelligence
            ↓
        Decision
            ↓
        Risk
            ↓
        Adaptive Simulation

        pipeline.
        """

        # ---------------------------------------------------------
        # 1. Market state
        # ---------------------------------------------------------
        market_state = (
            self.market_state_monitor.update(
                order_book
            )
        )

        # ---------------------------------------------------------
        # 2. Live execution intelligence
        #
        # update_trade() has already built the latest
        # order-flow state from Binance executed trades.
        #
        # update_order_book() combines:
        #   - microstructure
        #   - order flow
        #   - liquidity
        #   - market impact
        # ---------------------------------------------------------
        intelligence_state = (
            self.intelligence_engine.update_order_book(
                order_book
            )
        )

        # ---------------------------------------------------------
        # 3. Execution decision
        # ---------------------------------------------------------
        decision = (
            self.decision_engine.evaluate(
                intelligence_state
            )
        )

        # ---------------------------------------------------------
        # 4. Risk assessment
        # ---------------------------------------------------------
        risk_assessment = (
            self.risk_engine.assess(
                decision=decision,
                requested_quantity=(
                    self.requested_quantity
                ),
            )
        )

        # ---------------------------------------------------------
        # 5. Adaptive execution simulation
        #
        # IMPORTANT:
        # This is simulation only.
        # No exchange order is submitted.
        # ---------------------------------------------------------
        simulation_result = (
            self.simulation.simulate(
                decision=decision,
                risk_assessment=risk_assessment,
            )
        )

        # ---------------------------------------------------------
        # 6. Complete result
        # ---------------------------------------------------------
        result = V6ExecutionEngineResult(
            market_state=market_state,
            intelligence_state=intelligence_state,
            decision=decision,
            risk_assessment=risk_assessment,
            simulation_result=simulation_result,
        )

        self._latest_result = result

        return result

    # =============================================================
    # RESET
    # =============================================================

    def reset(self) -> None:
        """
        Reset stateful analysis layers.
        """

        self.market_state_monitor = (
            V6MarketStateMonitor()
        )

        self.intelligence_engine.reset()

        self.decision_engine.reset()

        self._latest_result = None

        self._trade_callback_error_count = 0