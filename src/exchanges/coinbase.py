import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://api.exchange.coinbase.com"


class CoinbaseAdapter(ExchangeAdapter):
    name = "coinbase"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/products/{exchange_symbol}/ticker",
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

        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/products/{exchange_symbol}/book",
            params={
                "level": 2,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        bids = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in data["bids"][:limit]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in data["asks"][:limit]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )