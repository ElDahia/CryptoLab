import requests
from datetime import datetime, timezone

from src.exchanges.base import ExchangeAdapter
from src.exchanges.models import OrderBook, OrderBookLevel


BASE_URL = "https://api.kraken.com/0/public"


class KrakenAdapter(ExchangeAdapter):
    name = "kraken"

    def get_price(self, symbol: str = "BTC/USDT") -> float:
        base, quote = symbol.split("/")

        pair_map = {
            "BTC/USDT": "XBTUSDT",
            "BTC/USD": "XBTUSD",
            "ETH/USDT": "ETHUSDT",
            "ETH/USD": "ETHUSD",
        }

        exchange_symbol = pair_map.get(symbol)

        if exchange_symbol is None:
            raise ValueError(
                f"Unsupported Kraken symbol: {symbol}"
            )

        response = requests.get(
            f"{BASE_URL}/Ticker",
            params={"pair": exchange_symbol},
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data["error"]:
            raise RuntimeError(data["error"])

        ticker = next(iter(data["result"].values()))

        return float(ticker["c"][0])

    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ) -> OrderBook:

        pair_map = {
            "BTC/USDT": "XBTUSDT",
            "BTC/USD": "XBTUSD",
            "ETH/USDT": "ETHUSDT",
            "ETH/USD": "ETHUSD",
        }

        exchange_symbol = pair_map.get(symbol)

        if exchange_symbol is None:
            raise ValueError(
                f"Unsupported Kraken symbol: {symbol}"
            )

        response = requests.get(
            f"{BASE_URL}/Depth",
            params={
                "pair": exchange_symbol,
                "count": limit,
            },
            timeout=10,
        )
        response.raise_for_status()

        data = response.json()

        if data["error"]:
            raise RuntimeError(data["error"])

        book = next(iter(data["result"].values()))

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