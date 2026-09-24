from src.analysis.liquidity_profile import (
    calculate_liquidity_profile,
)
from src.exchanges.binance_orderbook_snapshot import (
    BinanceOrderBookSnapshot,
)


provider = BinanceOrderBookSnapshot()

print("========== LIQUIDITY PROFILE TEST ==========")
print("Fetching Binance order book...")

order_book, update_id = provider.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

profile = calculate_liquidity_profile(
    order_book,
)


print("\n========== MARKET ==========")

print("Exchange:", profile.exchange)
print("Symbol:", profile.symbol)
print("Snapshot update ID:", update_id)
print("Mid price:", profile.mid_price)


print("\n========== LIQUIDITY BANDS ==========")

for band in profile.bands:
    print(
        f"\n--- {band.distance_bps:g} bps ---"
    )

    print(
        "Bid quantity:",
        band.bid_quantity,
    )

    print(
        "Ask quantity:",
        band.ask_quantity,
    )

    print(
        "Bid notional:",
        band.bid_notional,
    )

    print(
        "Ask notional:",
        band.ask_notional,
    )

    print(
        "Total notional:",
        band.total_notional,
    )

    print(
        "Bid ratio:",
        band.bid_ratio,
    )

    print(
        "Ask ratio:",
        band.ask_ratio,
    )


print("\n============================================")
