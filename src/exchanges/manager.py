from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from src.exchanges.binance import BinanceAdapter
from src.exchanges.okx import OKXAdapter
from src.exchanges.bybit import BybitAdapter
from src.exchanges.coinbase import CoinbaseAdapter
from src.exchanges.kraken import KrakenAdapter
from src.exchanges.gate import GateAdapter
from src.exchanges.bitget import BitgetAdapter
from src.exchanges.kucoin import KuCoinAdapter
from src.exchanges.models import Quote
from src.exchanges.snapshot import MarketSnapshot


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


def fetch_quote(exchange, symbol: str) -> Quote:
    price = exchange.get_price(symbol)

    return Quote(
        exchange=exchange.name,
        symbol=symbol,
        price=price,
        received_at=datetime.now(timezone.utc),
    )


def get_market_snapshot(
    symbol: str = "BTC/USDT",
) -> MarketSnapshot:

    cycle_started_at = datetime.now(timezone.utc)

    quotes = []

    with ThreadPoolExecutor(
        max_workers=len(EXCHANGE_ADAPTERS)
    ) as executor:

        futures = {
            executor.submit(fetch_quote, exchange, symbol): exchange
            for exchange in EXCHANGE_ADAPTERS
        }

        for future in as_completed(futures):
            exchange = futures[future]

            try:
                quote = future.result()
                quotes.append(quote)

            except Exception as error:
                print(f"{exchange.name} error: {error}")

    completed_at = datetime.now(timezone.utc)

    quotes.sort(key=lambda quote: quote.received_at)

    return MarketSnapshot(
        symbol=symbol,
        cycle_started_at=cycle_started_at,
        completed_at=completed_at,
        quotes=quotes,
    )


def filter_fresh_quotes(
    quotes: list[Quote],
    max_age_seconds: float = 5.0,
    reference_time: datetime | None = None,
) -> list[Quote]:

    if reference_time is None:
        reference_time = datetime.now(timezone.utc)

    return [
        quote
        for quote in quotes
        if (
            reference_time - quote.received_at
        ).total_seconds() <= max_age_seconds
    ]