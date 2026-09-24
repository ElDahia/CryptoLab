import requests

from src.exchanges.models import OrderBook, OrderBookLevel


class BinanceOrderBookSnapshot:
    """
    Binance REST order book snapshot provider.

    Returns both the normalized OrderBook and the
    Binance snapshot lastUpdateId required for
    WebSocket synchronization.
    """

    BASE_URL = "https://api.binance.com/api/v3"

    def get_snapshot(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5000,
    ) -> tuple[OrderBook, int]:

        if limit <= 0:
            raise ValueError(
                "limit must be greater than zero"
            )

        if limit > 5000:
            raise ValueError(
                "limit must not exceed 5000"
            )

        exchange_symbol = symbol.replace("/", "")

        response = requests.get(
            f"{self.BASE_URL}/depth",
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
            if float(quantity) > 0
        ]

        asks = [
            OrderBookLevel(
                price=float(price),
                quantity=float(quantity),
            )
            for price, quantity in data["asks"]
            if float(quantity) > 0
        ]

        order_book = OrderBook(
            exchange="binance",
            symbol=symbol,
            bids=bids,
            asks=asks,
            received_at=__import__(
                "datetime"
            ).datetime.now(
                __import__("datetime").timezone.utc
            ),
        )

        return order_book, int(data["lastUpdateId"])
