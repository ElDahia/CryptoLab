from datetime import datetime, timezone

from src.exchanges.models import OrderBook, OrderBookLevel
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskAssessment
from src.analysis.adaptive_execution_engine_v5 import (
    AdaptiveExecutionEngineV5,
)

now = datetime.now(timezone.utc)

order_book = OrderBook(
    exchange="test",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(price=99.0, quantity=10.0),
        OrderBookLevel(price=98.0, quantity=10.0),
        OrderBookLevel(price=97.0, quantity=10.0),
        OrderBookLevel(price=96.0, quantity=10.0),
    ],
    asks=[
        OrderBookLevel(price=101.0, quantity=2.0),
        OrderBookLevel(price=102.0, quantity=3.0),
        OrderBookLevel(price=103.0, quantity=5.0),
        OrderBookLevel(price=104.0, quantity=10.0),
    ],
    received_at=now,
)

decision = ExecutionDecision(
    exchange="test",
    symbol="BTC/USDT",
    timestamp=now,
    action="BUY",
    reason="V5.2 synthetic depth-aware test",
    confidence=1.0,
    buy_score=1.0,
    sell_score=0.0,
    market_impact_percent=0.0,
    spread_percent=1.0,
    imbalance=0.0,
    weighted_imbalance=0.0,
    net_volume=0.0,
    cvd=0.0,
    fully_filled=True,
)

risk = RiskAssessment(
    exchange="test",
    symbol="BTC/USDT",
    timestamp=now,
    approved=True,
    action="BUY",
    requested_quantity=8.0,
    allowed_quantity=8.0,
    reason="V5.2 synthetic depth-aware test",
    confidence=1.0,
    market_impact_percent=0.0,
    spread_percent=1.0,
    position_quantity=0.0,
    projected_position_quantity=8.0,
    daily_pnl=0.0,
    risk_score=0.0,
)

engine = AdaptiveExecutionEngineV5(
    max_slices=10,
    minimum_slice_quantity=0.01,
    max_impact_percent=5.0,
    max_spread_percent=10.0,
    impact_search_iterations=18,
    max_slice_fraction_of_liquidity=1.0,
    max_levels_per_slice=1,
)

result = engine.simulate(
    order_book=order_book,
    decision=decision,
    risk_assessment=risk,
)

print("DYNAMIC DEPTH-AWARE EXECUTION V5.2")
print()
print("Requested:", result.requested_quantity)
print("Planned:", result.planned_quantity)
print("Filled:", result.filled_quantity)
print("Unfilled:", result.unfilled_quantity)
print("Fill ratio:", result.fill_ratio)
print("Average execution:", result.average_execution_price)
print("Total notional:", result.total_notional)
print("Slippage %:", result.total_slippage_percent)
print("Market impact %:", result.total_market_impact_percent)
print("Fully filled:", result.fully_filled)
print("Slices:", result.slice_count)
print()

for execution_slice in result.slices:
    print(
        f"Slice #{execution_slice.sequence}: "
        f"qty={execution_slice.quantity:.6f} | "
        f"avg={execution_slice.average_execution_price:.6f} | "
        f"impact={execution_slice.market_impact_percent:.6f}% | "
        f"slippage={execution_slice.slippage_percent:.6f}% | "
        f"levels={execution_slice.levels_consumed} | "
        f"remaining={execution_slice.remaining_quantity:.6f} | "
        f"liquidity={execution_slice.remaining_liquidity:.6f}"
    )

print()
print("VALIDATION")
print(
    "Correct requested quantity:",
    result.requested_quantity == 8.0,
)
print(
    "No overfill:",
    result.filled_quantity
    <= result.planned_quantity + 1e-9,
)
print(
    "Execution completed:",
    result.fully_filled,
)
print(
    "Multiple adaptive slices:",
    result.slice_count > 1,
)
print(
    "Depth limit respected:",
    all(
        execution_slice.levels_consumed <= 1
        for execution_slice in result.slices
    ),
)
print(
    "Remaining quantity decreases:",
    all(
        result.slices[i].remaining_quantity
        < result.slices[i - 1].remaining_quantity
        for i in range(1, len(result.slices))
    ),
)
print(
    "Remaining liquidity decreases:",
    all(
        result.slices[i].remaining_liquidity
        < result.slices[i - 1].remaining_liquidity
        for i in range(1, len(result.slices))
    ),
)
