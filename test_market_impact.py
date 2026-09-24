from datetime import datetime, timezone

from src.analysis.market_impact import simulate_market_order
from src.exchanges.models import OrderBook, OrderBookLevel


order_book = OrderBook(
    exchange="test",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(100.0, 2.0),
        OrderBookLevel(99.0, 3.0),
        OrderBookLevel(98.0, 5.0),
    ],
    asks=[
        OrderBookLevel(101.0, 2.0),
        OrderBookLevel(102.0, 3.0),
        OrderBookLevel(103.0, 5.0),
    ],
    received_at=datetime.now(timezone.utc),
)


print("========== MARKET IMPACT TEST ==========")


print("\n========== BUY 4 BTC ==========")

buy = simulate_market_order(
    order_book=order_book,
    side="buy",
    quantity=4.0,
)

print("Requested:", buy.requested_quantity)
print("Filled:", buy.filled_quantity)
print("Average price:", buy.average_execution_price)
print("Reference price:", buy.reference_price)
print("Slippage:", buy.slippage)
print("Slippage %:", buy.slippage_percent)
print("Price impact:", buy.price_impact)
print("Impact %:", buy.price_impact_percent)
print("Total notional:", buy.total_notional)
print("Levels consumed:", buy.levels_consumed)
print("Fully filled:", buy.fully_filled)


print("\nExecution levels:")

for level in buy.execution_levels:
    print(
        "Price:",
        level.price,
        "| Available:",
        level.quantity,
        "| Filled:",
        level.filled_quantity,
        "| Notional:",
        level.notional,
    )


print("\n========== SELL 4 BTC ==========")

sell = simulate_market_order(
    order_book=order_book,
    side="sell",
    quantity=4.0,
)

print("Requested:", sell.requested_quantity)
print("Filled:", sell.filled_quantity)
print("Average price:", sell.average_execution_price)
print("Reference price:", sell.reference_price)
print("Slippage:", sell.slippage)
print("Slippage %:", sell.slippage_percent)
print("Price impact:", sell.price_impact)
print("Impact %:", sell.price_impact_percent)
print("Total notional:", sell.total_notional)
print("Levels consumed:", sell.levels_consumed)
print("Fully filled:", sell.fully_filled)


print("\nExecution levels:")

for level in sell.execution_levels:
    print(
        "Price:",
        level.price,
        "| Available:",
        level.quantity,
        "| Filled:",
        level.filled_quantity,
        "| Notional:",
        level.notional,
    )


print("\n========== PARTIAL FILL TEST ==========")

partial = simulate_market_order(
    order_book=order_book,
    side="buy",
    quantity=20.0,
)

print("Requested:", partial.requested_quantity)
print("Filled:", partial.filled_quantity)
print("Unfilled:", partial.unfilled_quantity)
print("Fully filled:", partial.fully_filled)
print("Levels consumed:", partial.levels_consumed)

print("========================================")
