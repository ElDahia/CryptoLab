import requests


BASE_URL = "https://api.bitget.com/api/v2"


def get_price(symbol: str = "BTCUSDT") -> float:
    response = requests.get(
        f"{BASE_URL}/spot/market/tickers",
        params={"symbol": symbol, "productType": "usdt-spot"},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if data.get("code") != "00000" or not data.get("data"):
        raise RuntimeError(data)

    return float(data["data"][0]["lastPr"])