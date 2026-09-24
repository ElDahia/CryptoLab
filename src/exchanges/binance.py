import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel
from src.analysis.microstructure import MarketTrade


BASE_URL = "https://api.binance.com/api/v3"


class BinanceAdapter(ExchangeAdapter):
    name = "binance"

    def get_price(
        self,
        symbol: str = "BTC/USDT",
    ) -> float:
        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{BASE_URL}/ticker/price",
            params={
                "symbol": exchange_symbol,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return float(data["price"])

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:
        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{BASE_URL}/depth",
            params={
                "symbol": exchange_symbol,
                "limit": limit,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        bids = [
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in data["bids"]
        ]

        asks = [
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in data["asks"]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )

    def get_recent_trades(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 20,
    ) -> list[MarketTrade]:
        """
        Fetch recent executed trades from Binance.

        Binance provides a native trade ID for every
        returned trade. CryptoLab preserves that ID
        inside MarketTrade for reliable deduplication.
        """

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        if limit > 1000:
            raise ValueError(
                "limit must not exceed 1000"
            )

        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{BASE_URL}/trades",
            params={
                "symbol": exchange_symbol,
                "limit": limit,
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        trades = []

        for trade in data:
            timestamp = datetime.fromtimestamp(
                trade["time"] / 1000,
                tz=timezone.utc,
            )

            trades.append(
                MarketTrade(
                    exchange=self.name,
                    symbol=symbol,
                    price=float(trade["price"]),
                    quantity=float(trade["qty"]),
                    timestamp=timestamp,
                    is_buyer_maker=bool(
                        trade["isBuyerMaker"]
                    ),
                    trade_id=trade["id"],
                )
            )

        return trades