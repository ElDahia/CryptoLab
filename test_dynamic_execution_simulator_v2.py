from datetime import datetime, timezone

from src.exchanges.models import OrderBook, OrderBookLevel
from src.analysis.execution_planner import ExecutionPlan, ExecutionSlice
from src.analysis.dynamic_execution_simulator_v2 import (
    DynamicExecutionSimulatorV2,
)


now = datetime.now(timezone.utc)

order_book = OrderBook(
    exchange="test",
    symbol="BTC/USDT",
    bids=[
        OrderBookLevel(price=99.0, quantity=5.0),
        OrderBookLevel(price=98.0, quantity=5.0),
    ],
    asks=[
        OrderBookLevel(price=101.0, quantity=5.0),
        OrderBookLevel(price=102.0, quantity=5.0),
    ],
    received_at=now,
)

plan = ExecutionPlan(
    exchange="test",
    symbol="BTC/USDT",
    action="BUY",
    requested_quantity=8.0,
    planned_quantity=8.0,
    remaining_quantity=0.0,
    slice_count=2,
    slices=(
        ExecutionSlice(
            sequence=1,
            action="BUY",
            quantity=5.0,
            max_impact_percent=10.0,
            max_spread_percent=10.0,
        ),
        ExecutionSlice(
            sequence=2,
            action="BUY",
            quantity=3.0,
            max_impact_percent=10.0,
            max_spread_percent=10.0,
        ),
    ),
    reason="dynamic V2 test",
    created_at=now,
)

simulator = DynamicExecutionSimulatorV2()

result = simulator.simulate(
    order_book=order_book,
    plan=plan,
)

print("DYNAMIC EXECUTION SIMULATOR V2")
print()
print("Requested:", result.requested_quantity)
print("Filled:", result.filled_quantity)
print("Unfilled:", result.unfilled_quantity)
print("Average execution:", result.average_execution_price)
print("Fill ratio:", result.fill_ratio)
print("Fully filled:", result.fully_filled)
print("Executed slices:", result.slice_count)
print()

for fill in result.fills:
    print(
        f"Slice #{fill.sequence}: "
        f"requested={fill.requested_quantity:.6f} | "
        f"filled={fill.filled_quantity:.6f} | "
        f"avg={fill.average_execution_price:.6f} | "
        f"levels={fill.levels_consumed}"
    )

print()
print("VALIDATION")
print("Full fill:", result.fully_filled)
print("Correct quantity:", abs(result.filled_quantity - 8.0) < 1e-9)
print("Two sequential slices:", result.slice_count == 2)
print(
    "Second slice reached deeper liquidity:",
    len(result.fills) == 2
    and result.fills[1].levels_consumed >= 1,
)
