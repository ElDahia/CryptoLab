from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.binance import BinanceAdapter
from src.exchanges.okx import OKXAdapter
from src.exchanges.bybit import BybitAdapter
from src.exchanges.coinbase import CoinbaseAdapter
from src.exchanges.kraken import KrakenAdapter
from src.exchanges.gate import GateAdapter
from src.exchanges.bitget import BitgetAdapter
from src.exchanges.kucoin import KuCoinAdapter
from src.exchanges.models import OrderBook
from src.analysis.microstructure import (
    MarketMicrostructureSnapshot,
    OrderBookMetrics,
    calculate_order_book_metrics,
)


EXCHANGE_ADAPTERS = [
    BinanceAdapter(),
    OKXAdapter(),
    BybitAdapter(),
    CoinbaseAdapter(),
    KrakenAdapter(),
    GateAdapter(),
    BitgetAdapter(),
    KuCoinAdapter(),
]


@dataclass(frozen=True)
class OrderBookSnapshot:
    symbol: str
    started_at: datetime
    completed_at: datetime
    order_books: list[OrderBook]

    @property
    def duration_seconds(self) -> float:
        return (
            self.completed_at - self.started_at
        ).total_seconds()

    @property
    def exchange_count(self) -> int:
        return len(self.order_books)

    @property
    def best_bid_exchange(self) -> OrderBook:
        if not self.order_books:
            raise ValueError(
                "Snapshot contains no order books"
            )

        return max(
            self.order_books,
            key=lambda book: book.best_bid.price,
        )

    @property
    def best_ask_exchange(self) -> OrderBook:
        if not self.order_books:
            raise ValueError(
                "Snapshot contains no order books"
            )

        return min(
            self.order_books,
            key=lambda book: book.best_ask.price,
        )

    @property
    def cross_exchange_spread(self) -> float:
        return (
            self.best_bid_exchange.best_bid.price
            - self.best_ask_exchange.best_ask.price
        )

    @property
    def cross_exchange_spread_percent(self) -> float:
        best_ask = self.best_ask_exchange.best_ask.price

        if best_ask <= 0:
            raise ValueError(
                "Best ask price must be greater than zero"
            )

        return (
            self.cross_exchange_spread
            / best_ask
        ) * 100


def fetch_order_book(
    exchange,
    symbol: str,
    limit: int,
) -> OrderBook:

    return exchange.get_order_book(
        symbol=symbol,
        limit=limit,
    )


def get_order_book_snapshot(
    symbol: str = "BTC/USDT",
    limit: int = 5,
) -> OrderBookSnapshot:

    started_at = datetime.now(timezone.utc)

    order_books = []

    with ThreadPoolExecutor(
        max_workers=len(EXCHANGE_ADAPTERS)
    ) as executor:

        futures = {
            executor.submit(
                fetch_order_book,
                exchange,
                symbol,
                limit,
            ): exchange
            for exchange in EXCHANGE_ADAPTERS
        }

        for future in as_completed(futures):
            exchange = futures[future]

            try:
                order_book = future.result()
                order_books.append(order_book)

            except Exception as error:
                print(
                    f"{exchange.name} order book error: {error}"
                )

    completed_at = datetime.now(timezone.utc)

    order_books.sort(
        key=lambda book: book.received_at
    )

    return OrderBookSnapshot(
        symbol=symbol,
        started_at=started_at,
        completed_at=completed_at,
        order_books=order_books,
    )


def build_microstructure_snapshot(
    order_book: OrderBook,
    depth_levels: int = 5,
) -> MarketMicrostructureSnapshot:
    """
    Convert a normalized OrderBook into a
    MarketMicrostructureSnapshot.
    """

    metrics = calculate_order_book_metrics(
        order_book,
        depth_levels=depth_levels,
    )

    return MarketMicrostructureSnapshot(
        exchange=order_book.exchange,
        symbol=order_book.symbol,
        timestamp=order_book.received_at,
        order_book=metrics,
    )


def build_microstructure_snapshots(
    snapshot: OrderBookSnapshot,
    depth_levels: int = 5,
) -> list[MarketMicrostructureSnapshot]:
    """
    Build microstructure metrics for every exchange
    successfully collected in an order-book snapshot.
    """

    return [
        build_microstructure_snapshot(
            order_book,
            depth_levels=depth_levels,
        )
        for order_book in snapshot.order_books
    ]