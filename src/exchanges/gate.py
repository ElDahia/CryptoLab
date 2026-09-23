import requests


BASE_URL = "https://api.gateio.ws/api/v4"


def get_price(symbol: str = "BTC_USDT") -> float:
    response = requests.get(
        f"{BASE_URL}/spot/tickers",
        params={"currency_pair": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()

    if not data:
        raise RuntimeError("No market data returned")

    return float(data[0]["last"])