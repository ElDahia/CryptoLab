import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://api.kucoin.com/api/v1"


class KuCoinAdapter(ExchangeAdapter):
    name = "kucoin"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/market/orderbook/level1",
            params={"symbol": exchange_symbol},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code") != "200000":
            raise RuntimeError(data)

        return float(data["data"]["price"])

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:

        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/market/orderbook/level2_20",
            params={"symbol": exchange_symbol},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code") != "200000":
            raise RuntimeError(data)

        book = data["data"]

        bids = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["bids"][:limit]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["asks"][:limit]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )