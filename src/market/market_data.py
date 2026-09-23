import requests
import pandas as pd


BASE_URL = "https://api.binance.com/api/v3"


def get_price(symbol: str = "BTCUSDT") -> float:
    response = requests.get(
        f"{BASE_URL}/ticker/price",
        params={"symbol": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return float(data["price"])


def get_klines(
    symbol: str = "BTCUSDT",
    interval: str = "1h",
    limit: int = 100,
) -> pd.DataFrame:

    response = requests.get(
        f"{BASE_URL}/klines",
        params={
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_volume",
        "trades",
        "taker_buy_base",
        "taker_buy_quote",
        "ignore",
    ]

    df = pd.DataFrame(data, columns=columns)

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column])

    return df


if __name__ == "__main__":
    print("BTC price:", get_price())

    candles = get_klines("BTCUSDT", "1h", 10)
    print(candles[["open_time", "open", "high", "low", "close", "volume"]])
