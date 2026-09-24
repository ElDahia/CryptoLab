from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class V6MarketState:
    update_number: int
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_percent: float
    bid_depth_quantity: float
    ask_depth_quantity: float
    total_depth_quantity: float
    mid_price_change: float
    mid_price_change_percent: float
    bid_depth_change: float
    ask_depth_change: float

    @property
    def liquidity_change(self) -> float:
        return (
            self.bid_depth_change
            + self.ask_depth_change
        )


class V6MarketStateMonitor:
    def __init__(self) -> None:
        self._previous_book: Optional[OrderBook] = None
        self._update_number = 0
        self._latest_state: Optional[V6MarketState] = None

    @staticmethod
    def _mid_price(order_book: OrderBook) -> float:
        return (
            order_book.best_bid.price
            + order_book.best_ask.price
        ) / 2.0

    @staticmethod
    def _depth_quantity(
        order_book: OrderBook,
    ) -> tuple[float, float]:
        bid_depth = sum(
            level.quantity
            for level in order_book.bids
        )

        ask_depth = sum(
            level.quantity
            for level in order_book.asks
        )

        return bid_depth, ask_depth

    def update(
        self,
        order_book: OrderBook,
    ) -> V6MarketState:
        self._update_number += 1

        best_bid = order_book.best_bid.price
        best_ask = order_book.best_ask.price
        mid_price = self._mid_price(order_book)

        spread = best_ask - best_bid

        spread_percent = (
            spread / best_bid
        ) * 100.0

        bid_depth, ask_depth = (
            self._depth_quantity(order_book)
        )

        if self._previous_book is None:
            mid_price_change = 0.0
            mid_price_change_percent = 0.0
            bid_depth_change = 0.0
            ask_depth_change = 0.0

        else:
            previous_mid = self._mid_price(
                self._previous_book
            )

            previous_bid_depth, previous_ask_depth = (
                self._depth_quantity(
                    self._previous_book
                )
            )

            mid_price_change = (
                mid_price - previous_mid
            )

            mid_price_change_percent = (
                (
                    mid_price_change
                    / previous_mid
                ) * 100.0
                if previous_mid > 0
                else 0.0
            )

            bid_depth_change = (
                bid_depth - previous_bid_depth
            )

            ask_depth_change = (
                ask_depth - previous_ask_depth
            )

        state = V6MarketState(
            update_number=self._update_number,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            spread=spread,
            spread_percent=spread_percent,
            bid_depth_quantity=bid_depth,
            ask_depth_quantity=ask_depth,
            total_depth_quantity=(
                bid_depth + ask_depth
            ),
            mid_price_change=mid_price_change,
            mid_price_change_percent=(
                mid_price_change_percent
            ),
            bid_depth_change=bid_depth_change,
            ask_depth_change=ask_depth_change,
        )

        self._previous_book = order_book
        self._latest_state = state

        return state

    @property
    def latest_state(self) -> Optional[V6MarketState]:
        return self._latest_state
