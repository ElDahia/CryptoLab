import requests


BASE_URL = "https://api.kucoin.com/api/v1"


def get_price(symbol: str = "BTC-USDT") -> float:
    response = requests.get(
        f"{BASE_URL}/market/orderbook/level1",
        params={"symbol": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("code") != "200000":
        raise RuntimeError(data)

    return float(data["data"]["price"])