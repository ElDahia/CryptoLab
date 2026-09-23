from src.market.market_data import get_price


def main():
    btc_price = get_price("BTCUSDT")
    print(f"BTC/USDT: {btc_price}")


if __name__ == "__main__":
    main()
