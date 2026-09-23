import requests


BASE_URL = "https://api.kraken.com/0/public"


def get_price(symbol: str = "XBTUSD") -> float:
    response = requests.get(
        f"{BASE_URL}/Ticker",
        params={"pair": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if data["error"]:
        raise RuntimeError(data["error"])

    ticker = next(iter(data["result"].values()))
    return float(ticker["c"][0])