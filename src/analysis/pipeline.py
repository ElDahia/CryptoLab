import pandas as pd

from src.market.market_data import get_klines
from src.analysis.indicators import (
    add_sma,
    add_ema,
    add_rsi,
    add_macd,
    add_bollinger_bands,
)
from src.analysis.markets import MARKETS


def build_market_data(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
) -> pd.DataFrame:

    df = get_klines(symbol, interval, limit)

    df = add_sma(df)
    df = add_ema(df)
    df = add_rsi(df)
    df = add_macd(df)
    df = add_bollinger_bands(df)

    return df


def build_all_markets(
    interval: str = "1h",
    limit: int = 100,
) -> dict[str, pd.DataFrame]:

    results = {}

    for symbol in MARKETS:
        results[symbol] = build_market_data(
            symbol,
            interval,
            limit,
        )

    return results