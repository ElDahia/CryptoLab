from src.analysis.liquidity_profile import (
    calculate_liquidity_profile,
)
from src.analysis.market_impact import (
    simulate_market_order,
)
from src.exchanges.binance_orderbook_snapshot import (
    BinanceOrderBookSnapshot,
)


provider = BinanceOrderBookSnapshot()

print("========== LIQUIDITY ? IMPACT VALIDATION ==========")
print("Fetching Binance snapshot...")

order_book, update_id = provider.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

profile = calculate_liquidity_profile(
    order_book,
)


print("\nSnapshot update ID:", update_id)
print("Mid price:", profile.mid_price)


print("\n========== PROFILE ==========")

for band in profile.bands:
    print(
        f"{band.distance_bps:g} bps | "
        f"Bid: {band.bid_quantity:.8f} BTC | "
        f"Ask: {band.ask_quantity:.8f} BTC"
    )


print("\n========== MARKET IMPACT ==========")

for side in ("buy", "sell"):

    print(f"\n--- {side.upper()} ---")

    result = simulate_market_order(
        order_book=order_book,
        side=side,
        quantity=1.0,
    )

    print(
        "Requested:",
        result.requested_quantity,
    )

    print(
        "Filled:",
        result.filled_quantity,
    )

    print(
        "Average execution:",
        result.average_execution_price,
    )

    print(
        "Reference price:",
        result.reference_price,
    )

    print(
        "Slippage:",
        result.slippage,
    )

    print(
        "Slippage %:",
        result.slippage_percent,
    )

    print(
        "Levels consumed:",
        result.levels_consumed,
    )

    print(
        "Fully filled:",
        result.fully_filled,
    )


print("\n========== DEEP EXECUTION ==========")

for side in ("buy", "sell"):

    result = simulate_market_order(
        order_book=order_book,
        side=side,
        quantity=10.0,
    )

    print(
        f"\n{side.upper()} 10 BTC"
    )

    print(
        "Filled:",
        result.filled_quantity,
    )

    print(
        "Unfilled:",
        result.unfilled_quantity,
    )

    print(
        "Average execution:",
        result.average_execution_price,
    )

    print(
        "Slippage %:",
        result.slippage_percent,
    )

    print(
        "Levels consumed:",
        result.levels_consumed,
    )

    print(
        "Fully filled:",
        result.fully_filled,
    )


print("\n====================================================")
