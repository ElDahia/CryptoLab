import requests


BASE_URL = "https://www.okx.com/api/v5"


def get_price(symbol: str = "BTC-USDT") -> float:
    response = requests.get(
        f"{BASE_URL}/market/ticker",
        params={"instId": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return float(data["data"][0]["last"])