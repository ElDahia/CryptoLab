import requests


BASE_URL = "https://api.binance.com/api/v3"


def get_price(symbol: str = "BTCUSDT") -> float:
    response = requests.get(
        f"{BASE_URL}/ticker/price",
        params={"symbol": symbol},
        timeout=10,
    )
    response.raise_for_status()

    return float(response.json()["price"])