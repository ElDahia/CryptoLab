import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://api.gateio.ws/api/v4"


class GateAdapter(ExchangeAdapter):
    name = "gate"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        base, quote = symbol.split("/")
        exchange_symbol = f"{base}_{quote}"

        response = requests.get(
            f"{BASE_URL}/spot/tickers",
            params={"currency_pair": exchange_symbol},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if not data:
            raise RuntimeError("No market data returned")

        return float(data[0]["last"])

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:

        base, quote = symbol.split("/")
        exchange_symbol = f"{base}_{quote}"

        response = requests.get(
            f"{BASE_URL}/spot/order_book",
            params={
                "currency_pair": exchange_symbol,
                "limit": limit,
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
            for level in data["bids"]
        ]

        asks = [
            OrderBookLevel(
                price=float(level[0]),
                quantity=float(level[1]),
            )
            for level in data["asks"]
        ]

        return OrderBook(
            exchange=self.name,
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=datetime.now(timezone.utc),
        )