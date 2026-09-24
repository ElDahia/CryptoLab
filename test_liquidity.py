from src.analysis.liquidity import calculate_liquidity_metrics
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot


provider = BinanceOrderBookSnapshot()

print("========== LIVE LIQUIDITY TEST ==========")

print("Fetching Binance order book...")

order_book, update_id = provider.get_snapshot(
    symbol="BTC/USDT",
    limit=100,
)

metrics = calculate_liquidity_metrics(
    order_book,
    depth_levels=5,
)


print("\n========== MARKET ==========")

print("Exchange:", metrics.exchange)
print("Symbol:", metrics.symbol)

print("Snapshot update ID:", update_id)

print("Mid price:", metrics.mid_price)
print("Spread:", metrics.spread)
print("Spread %:", metrics.spread_percent)


print("\n========== DEPTH ==========")

print(
    "Bid depth quantity:",
    metrics.bid_depth_quantity,
)

print(
    "Ask depth quantity:",
    metrics.ask_depth_quantity,
)

print(
    "Bid depth notional:",
    metrics.bid_depth_notional,
)

print(
    "Ask depth notional:",
    metrics.ask_depth_notional,
)

print(
    "Total depth quantity:",
    metrics.total_depth_quantity,
)

print(
    "Total depth notional:",
    metrics.total_depth_notional,
)


print("\n========== LIQUIDITY DISTRIBUTION ==========")

print(
    "Bid liquidity ratio:",
    metrics.bid_liquidity_ratio,
)

print(
    "Ask liquidity ratio:",
    metrics.ask_liquidity_ratio,
)

print(
    "Bid notional ratio:",
    metrics.bid_notional_ratio,
)

print(
    "Ask notional ratio:",
    metrics.ask_notional_ratio,
)


print("\n========== CONCENTRATION ==========")

print(
    "Bid concentration:",
    metrics.bid_concentration,
)

print(
    "Ask concentration:",
    metrics.ask_concentration,
)

print("==========================================")
