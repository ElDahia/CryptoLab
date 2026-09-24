from __future__ import annotations

import time
from dataclasses import dataclass

from src.analysis.market_impact import simulate_market_order
from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.exchanges.models import OrderBook


@dataclass(frozen=True)
class V6ExecutionSlice:
    sequence: int
    requested_quantity: float
    filled_quantity: float
    average_execution_price: float
    total_notional: float
    reference_price: float
    slippage_percent: float
    market_impact_percent: float
    levels_consumed: int
    feed_update_number: int
    timestamp: float


@dataclass(frozen=True)
class V6ExecutionResult:
    requested_quantity: float
    filled_quantity: float
    unfilled_quantity: float
    average_execution_price: float
    total_notional: float
    slippage_percent: float
    market_impact_percent: float
    slices: tuple[V6ExecutionSlice, ...]

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0:
            return 0.0

        return self.filled_quantity / self.requested_quantity

    @property
    def fully_filled(self) -> bool:
        return self.unfilled_quantity <= 1e-9


class V6ExecutionSimulator:
    def __init__(
        self,
        feed: V6LiveMarketFeed,
        slice_quantity: float = 0.5,
        update_timeout_seconds: float = 5.0,
    ) -> None:
        if slice_quantity <= 0:
            raise ValueError(
                "slice_quantity must be greater than zero"
            )

        if update_timeout_seconds <= 0:
            raise ValueError(
                "update_timeout_seconds must be greater than zero"
            )

        self.feed = feed
        self.slice_quantity = slice_quantity
        self.update_timeout_seconds = update_timeout_seconds

    def _wait_for_initial_book(self) -> tuple[OrderBook, int]:
        deadline = (
            time.monotonic()
            + self.update_timeout_seconds
        )

        while time.monotonic() < deadline:
            if (
                self.feed.is_synchronized
                and self.feed.update_count > 0
                and self.feed.latest_order_book is not None
            ):
                return (
                    self.feed.get_latest_order_book(),
                    self.feed.update_count,
                )

            time.sleep(0.01)

        raise TimeoutError(
            "Timed out waiting for the first validated Binance order book"
        )

    def _wait_for_new_book(
        self,
        previous_update_count: int,
    ) -> tuple[OrderBook, int]:
        deadline = (
            time.monotonic()
            + self.update_timeout_seconds
        )

        while time.monotonic() < deadline:
            if (
                self.feed.is_synchronized
                and self.feed.update_count
                > previous_update_count
                and self.feed.latest_order_book is not None
            ):
                return (
                    self.feed.get_latest_order_book(),
                    self.feed.update_count,
                )

            time.sleep(0.01)

        raise TimeoutError(
            "Timed out waiting for a new validated Binance order book update"
        )

    def simulate(
        self,
        requested_quantity: float,
        action: str = "BUY",
    ) -> V6ExecutionResult:
        if requested_quantity <= 0:
            raise ValueError(
                "requested_quantity must be greater than zero"
            )

        action = action.upper()

        if action not in {"BUY", "SELL"}:
            raise ValueError(
                "action must be BUY or SELL"
            )

        if not self.feed.is_synchronized:
            raise RuntimeError(
                "V6 market feed is not synchronized"
            )

        first_book, current_update_count = (
            self._wait_for_initial_book()
        )

        remaining_quantity = requested_quantity
        total_filled = 0.0
        total_notional = 0.0

        slices: list[V6ExecutionSlice] = []

        sequence = 0

        while remaining_quantity > 1e-9:
            sequence += 1

            current_book = (
                first_book
                if sequence == 1
                else self.feed.get_latest_order_book()
            )

            quantity = min(
                self.slice_quantity,
                remaining_quantity,
            )

            impact = simulate_market_order(
                order_book=current_book,
                side=action,
                quantity=quantity,
            )

            if impact.filled_quantity <= 0:
                raise RuntimeError(
                    "No liquidity available for V6 execution slice"
                )

            reference_price = (
                current_book.best_ask.price
                if action == "BUY"
                else current_book.best_bid.price
            )

            slices.append(
                V6ExecutionSlice(
                    sequence=sequence,
                    requested_quantity=quantity,
                    filled_quantity=impact.filled_quantity,
                    average_execution_price=impact.average_execution_price,
                    total_notional=impact.total_notional,
                    reference_price=reference_price,
                    slippage_percent=impact.slippage_percent,
                    market_impact_percent=impact.price_impact_percent,
                    levels_consumed=impact.levels_consumed,
                    feed_update_number=current_update_count,
                    timestamp=time.time(),
                )
            )

            total_filled += impact.filled_quantity
            total_notional += impact.total_notional

            remaining_quantity = max(
                0.0,
                requested_quantity - total_filled,
            )

            if remaining_quantity <= 1e-9:
                break

            previous_update_count = current_update_count

            _, current_update_count = (
                self._wait_for_new_book(
                    previous_update_count
                )
            )

        average_execution_price = (
            total_notional / total_filled
            if total_filled > 0
            else 0.0
        )

        initial_reference_price = (
            slices[0].reference_price
        )

        if action == "BUY":
            aggregate_slippage = (
                (
                    average_execution_price
                    - initial_reference_price
                )
                / initial_reference_price
            ) * 100
        else:
            aggregate_slippage = (
                (
                    initial_reference_price
                    - average_execution_price
                )
                / initial_reference_price
            ) * 100

        unfilled_quantity = max(
            0.0,
            requested_quantity - total_filled,
        )

        return V6ExecutionResult(
            requested_quantity=requested_quantity,
            filled_quantity=total_filled,
            unfilled_quantity=unfilled_quantity,
            average_execution_price=average_execution_price,
            total_notional=total_notional,
            slippage_percent=aggregate_slippage,
            market_impact_percent=aggregate_slippage,
            slices=tuple(slices),
        )
