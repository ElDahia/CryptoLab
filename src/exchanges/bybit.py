import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://api.bybit.com/v5"


class BybitAdapter(ExchangeAdapter):
    name = "bybit"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{BASE_URL}/market/tickers",
            params={
                "category": "spot",
                "symbol": exchange_symbol,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if (
            data.get("retCode") != 0
            or not data.get("result", {}).get("list")
        ):
            raise RuntimeError(data)

        return float(
            data["result"]["list"][0]["lastPrice"]
        )

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:

        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{BASE_URL}/market/orderbook",
            params={
                "category": "spot",
                "symbol": exchange_symbol,
                "limit": limit,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if (
            data.get("retCode") != 0
            or not data.get("result")
        ):
            raise RuntimeError(data)

        book = data["result"]

        bids = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["b"]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in book["a"]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )