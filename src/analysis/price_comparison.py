from src.exchanges.manager import get_all_prices
from src.exchanges.fees import FEES


def compare_prices() -> dict:
    prices = get_all_prices()

    valid_prices = {
        exchange: price
        for exchange, price in prices.items()
        if price is not None
    }

    if not valid_prices:
        raise RuntimeError("No valid exchange prices available")

    highest_exchange = max(valid_prices, key=valid_prices.get)
    lowest_exchange = min(valid_prices, key=valid_prices.get)

    highest_price = valid_prices[highest_exchange]
    lowest_price = valid_prices[lowest_exchange]

    spread = highest_price - lowest_price
    spread_percent = (spread / lowest_price) * 100

    return {
        "prices": valid_prices,
        "highest_exchange": highest_exchange,
        "highest_price": highest_price,
        "lowest_exchange": lowest_exchange,
        "lowest_price": lowest_price,
        "spread": spread,
        "spread_percent": spread_percent,
    }


def calculate_net_spread(
    buy_exchange: str,
    sell_exchange: str,
    buy_price: float,
    sell_price: float,
) -> dict:

    if buy_exchange not in FEES:
        raise ValueError(f"Unknown buy exchange: {buy_exchange}")

    if sell_exchange not in FEES:
        raise ValueError(f"Unknown sell exchange: {sell_exchange}")

    buy_fee = FEES[buy_exchange]
    sell_fee = FEES[sell_exchange]

    buy_cost = buy_price * (1 + buy_fee)
    sell_revenue = sell_price * (1 - sell_fee)

    net_profit = sell_revenue - buy_cost
    net_spread_percent = (net_profit / buy_cost) * 100

    return {
        "buy_exchange": buy_exchange,
        "sell_exchange": sell_exchange,
        "buy_fee": buy_fee,
        "sell_fee": sell_fee,
        "buy_cost": buy_cost,
        "sell_revenue": sell_revenue,
        "net_profit": net_profit,
        "net_spread_percent": net_spread_percent,
    }


def find_arbitrage_opportunities() -> list[dict]:
    prices = get_all_prices()

    valid_prices = {
        exchange: price
        for exchange, price in prices.items()
        if price is not None
    }

    opportunities = []

    for buy_exchange, buy_price in valid_prices.items():
        for sell_exchange, sell_price in valid_prices.items():

            if buy_exchange == sell_exchange:
                continue

            result = calculate_net_spread(
                buy_exchange=buy_exchange,
                sell_exchange=sell_exchange,
                buy_price=buy_price,
                sell_price=sell_price,
            )

            opportunities.append(result)

    opportunities.sort(
        key=lambda opportunity: opportunity["net_profit"],
        reverse=True,
    )

    return opportunities