from __future__ import annotations

from src.analysis.adaptive_execution_engine_v5 import (
    AdaptiveExecutionEngineV5,
    AdaptiveExecutionResultV5,
)
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.exchanges.models import OrderBook, OrderBookLevel


class V6ExecutionSimulation:
    """Simulation-only adapter from the validated V6 feed to V5 execution."""

    def __init__(
        self,
        feed: V6LiveMarketFeed,
        engine: AdaptiveExecutionEngineV5 | None = None,
    ) -> None:
        self.feed = feed
        self.engine = engine or AdaptiveExecutionEngineV5()

    def snapshot_order_book(self) -> OrderBook:
        """Return an independent copy of the feed's latest validated book."""
        if not self.feed.is_running:
            raise RuntimeError("V6 live market feed is not running")
        if not self.feed.is_synchronized:
            raise RuntimeError("V6 live market feed is not synchronized")

        live_book = self.feed.get_latest_order_book()
        return OrderBook(
            exchange=live_book.exchange,
            symbol=live_book.symbol,
            bids=[
                OrderBookLevel(level.price, level.quantity)
                for level in live_book.bids
            ],
            asks=[
                OrderBookLevel(level.price, level.quantity)
                for level in live_book.asks
            ],
            received_at=live_book.received_at,
        )

    def simulate(
        self,
        decision: ExecutionDecision,
        risk_assessment: RiskAssessment,
    ) -> AdaptiveExecutionResultV5:
        """Simulate against a private book copy; never submits exchange orders."""
        simulation_book = self.snapshot_order_book()
        return self.engine.simulate(
            order_book=simulation_book,
            decision=decision,
            risk_assessment=risk_assessment,
        )
