from src.analysis.live_market_impact import LiveMarketImpactEngine
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot

print("=" * 60)
print("LIVE MARKET IMPACT ENGINE TEST")
print("=" * 60)

snapshot_provider = BinanceOrderBookSnapshot()

order_book, update_id = snapshot_provider.get_snapshot(
    symbol="BTC/USDT",
    limit=1000,
)

print(f"Snapshot update ID: {update_id}")
print(f"Best bid: {order_book.best_bid.price}")
print(f"Best ask: {order_book.best_ask.price}")

buy_engine = LiveMarketImpactEngine(
    side="buy",
    quantity=10.0,
)

sell_engine = LiveMarketImpactEngine(
    side="sell",
    quantity=10.0,
)

buy_state = buy_engine.update(order_book)
sell_state = sell_engine.update(order_book)

print()
print("--- BUY 10 BTC ---")
print(f"Requested: {buy_state.requested_quantity}")
print(f"Filled: {buy_state.filled_quantity}")
print(f"Unfilled: {buy_state.unfilled_quantity}")
print(f"Average execution: {buy_state.average_execution_price}")
print(f"Reference price: {buy_state.reference_price}")
print(f"Slippage: {buy_state.slippage}")
print(f"Slippage %: {buy_state.slippage_percent}")
print(f"Price impact %: {buy_state.price_impact_percent}")
print(f"Levels consumed: {buy_state.levels_consumed}")
print(f"Fully filled: {buy_state.fully_filled}")

print()
print("--- SELL 10 BTC ---")
print(f"Requested: {sell_state.requested_quantity}")
print(f"Filled: {sell_state.filled_quantity}")
print(f"Unfilled: {sell_state.unfilled_quantity}")
print(f"Average execution: {sell_state.average_execution_price}")
print(f"Reference price: {sell_state.reference_price}")
print(f"Slippage: {sell_state.slippage}")
print(f"Slippage %: {sell_state.slippage_percent}")
print(f"Price impact %: {sell_state.price_impact_percent}")
print(f"Levels consumed: {sell_state.levels_consumed}")
print(f"Fully filled: {sell_state.fully_filled}")

print()
print("--- ENGINE ---")
print(f"Buy updates: {buy_engine.update_count}")
print(f"Sell updates: {sell_engine.update_count}")

print("=" * 60)
