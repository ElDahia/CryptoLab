import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://www.okx.com/api/v5"


class OKXAdapter(ExchangeAdapter):
    name = "okx"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/market/ticker",
            params={"instId": exchange_symbol},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code") != "0" or not data.get("data"):
            raise RuntimeError(data)

        return float(data["data"][0]["last"])

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:

        base, quote = symbol.split("/")
        exchange_symbol = f"{base}-{quote}"

        response = requests.get(
            f"{BASE_URL}/market/books",
            params={
                "instId": exchange_symbol,
                "sz": limit,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("code") != "0" or not data.get("data"):
            raise RuntimeError(data)

        book = data["data"][0]

        bids = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["bids"]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["asks"]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )