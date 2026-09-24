from datetime import datetime, timezone

from src.analysis.live_market_state import (
    LiveMarketStateEngine,
)
from src.analysis.live_microstructure import (
    LiveMicrostructureState,
)
from src.analysis.live_order_flow import (
    LiveOrderFlowState,
)
from src.analysis.microstructure import (
    OrderBookMetrics,
)


timestamp = datetime.now(timezone.utc)


metrics = OrderBookMetrics(
    exchange="binance",
    symbol="BTC/USDT",
    best_bid=83500.0,
    best_ask=83501.0,
    bid_quantity=1.5,
    ask_quantity=1.0,
    spread=1.0,
    spread_percent=0.0011976047904191617,
    mid_price=83500.5,
    bid_notional=125250.0,
    ask_notional=83501.0,
    imbalance=0.2,
    weighted_imbalance=0.25,
    bid_depth_quantity=3.0,
    ask_depth_quantity=2.0,
    bid_depth_notional=250500.0,
    ask_depth_notional=167002.0,
    bid_pressure=0.6,
    ask_pressure=0.4,
    weighted_bid_pressure=0.625,
    weighted_ask_pressure=0.375,
)


microstructure = LiveMicrostructureState(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=timestamp,
    metrics=metrics,
)


order_flow = LiveOrderFlowState(
    exchange="binance",
    symbol="BTC/USDT",
    timestamp=timestamp,
    trade_count=100,
    buy_volume=2.5,
    sell_volume=2.0,
    buy_notional=208750.0,
    sell_notional=167000.0,
    net_volume=0.5,
    net_notional=41750.0,
    buy_ratio=0.5555555556,
    sell_ratio=0.4444444444,
    cvd=0.5,
)


engine = LiveMarketStateEngine()


print("========== LIVE MARKET STATE TEST ==========")

print("\n========== INITIAL ==========")

print("Latest state:", engine.latest_state)
print("Update count:", engine.update_count)


print("\n========== MICROSTRUCTURE UPDATE ==========")

result = engine.update_microstructure(
    microstructure,
)

print("Combined state:", result)
print("Update count:", engine.update_count)


print("\n========== ORDER FLOW UPDATE ==========")

result = engine.update_order_flow(
    order_flow,
)

print("Combined state available:", result is not None)
print("Update count:", engine.update_count)


print("\n========== COMBINED MARKET STATE ==========")

state = engine.latest_state

if state is None:
    raise RuntimeError(
        "Combined market state was not created"
    )

print("Exchange:", state.exchange)
print("Symbol:", state.symbol)

print("Best bid:", state.best_bid)
print("Best ask:", state.best_ask)
print("Mid price:", state.mid_price)
print("Spread:", state.spread)

print("Imbalance:", state.imbalance)
print("Weighted imbalance:", state.weighted_imbalance)

print("Trade count:", state.trade_count)

print("Buy volume:", state.buy_volume)
print("Sell volume:", state.sell_volume)

print("Net volume:", state.net_volume)
print("Net notional:", state.net_notional)

print("Buy ratio:", state.buy_ratio)
print("Sell ratio:", state.sell_ratio)

print("CVD:", state.cvd)


print("\n========== ENGINE ==========")

print("Update count:", engine.update_count)
print("Has latest state:", engine.latest_state is not None)


print("\n========== RESET ==========")

engine.reset()

print("Latest state:", engine.latest_state)
print("Update count:", engine.update_count)

print("============================================")