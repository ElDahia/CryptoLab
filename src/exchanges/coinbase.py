import requests


BASE_URL = "https://api.exchange.coinbase.com"


def get_price(symbol: str = "BTC-USD") -> float:
    response = requests.get(
        f"{BASE_URL}/products/{symbol}/ticker",
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return float(data["price"])