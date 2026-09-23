import requests


def get_price(symbol: str = "BTCUSDT") -> float:
    url = "https://api.binance.com/api/v3/ticker/price"
    response = requests.get(
        url,
        params={"symbol": symbol},
        timeout=10,
    )
    response.raise_for_status()

    data = response.json()
    return float(data["price"])


if __name__ == "__main__":
    print("BTC price:", get_price())
