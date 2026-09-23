import requests


BASE_URL = "https://api.bybit.com/v5"


def get_price(symbol: str = "BTCUSDT") -> float:
    response = requests.get(
        f"{BASE_URL}/market/tickers",
        params={
            "category": "spot",
            "symbol": symbol,
        },
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return float(data["result"]["list"][0]["lastPrice"])