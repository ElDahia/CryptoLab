from src.analysis.execution_decision import ExecutionDecision
from src.analysis.execution_planner import ExecutionPlanner
from src.analysis.execution_simulator import ExecutionSimulator
from src.analysis.risk_engine import RiskEngine
from src.exchanges.binance_orderbook_snapshot import BinanceOrderBookSnapshot


def build_decision() -> ExecutionDecision:
    return ExecutionDecision(
        exchange="binance",
        symbol="BTC/USDT",
        timestamp=None,
        action="BUY",
        reason="execution simulation stress test",
        confidence=0.85,
        buy_score=0.85,
        sell_score=0.20,
        market_impact_percent=0.01,
        spread_percent=0.005,
        imbalance=0.30,
        weighted_imbalance=0.35,
        net_volume=2.0,
        cvd=2.0,
        fully_filled=True,
    )


def run_scenario(
    name: str,
    order_book,
    requested_quantity: float,
) -> None:
    print("\n" + "=" * 70)
    print(f"SCENARIO: {name}")
    print("=" * 70)

    decision = build_decision()

    risk_engine = RiskEngine(
        max_order_quantity=requested_quantity,
        max_position_quantity=requested_quantity * 2,
    )

    assessment = risk_engine.assess(
        decision=decision,
        requested_quantity=requested_quantity,
    )

    print("\n--- RISK ---")
    print(f"Approved: {assessment.approved}")
    print(f"Requested: {assessment.requested_quantity}")
    print(f"Allowed: {assessment.allowed_quantity}")
    print(f"Reason: {assessment.reason}")

    if not assessment.approved:
        print("\nRisk rejected the scenario.")
        return

    planner = ExecutionPlanner(
        default_slice_quantity=1.0,
        max_slices=20,
    )

    plan = planner.create_plan(
        decision=decision,
        risk_assessment=assessment,
    )

    print("\n--- EXECUTION PLAN ---")
    print(f"Action: {plan.action}")
    print(f"Requested quantity: {plan.requested_quantity}")
    print(f"Planned quantity: {plan.planned_quantity}")
    print(f"Remaining quantity: {plan.remaining_quantity}")
    print(f"Slice count: {plan.slice_count}")

    for execution_slice in plan.slices:
        print(
            f"Slice #{execution_slice.sequence}: "
            f"{execution_slice.action} "
            f"{execution_slice.quantity:.6f} BTC"
        )

    simulator = ExecutionSimulator()

    result = simulator.simulate(
        order_book=order_book,
        plan=plan,
    )

    print("\n--- EXECUTION SIMULATION ---")
    print(f"Action: {result.action}")
    print(f"Requested quantity: {result.requested_quantity}")
    print(f"Filled quantity: {result.filled_quantity}")
    print(f"Unfilled quantity: {result.unfilled_quantity}")
    print(f"Fill ratio: {result.fill_ratio:.6f}")
    print(f"Average execution price: {result.average_execution_price:.8f}")
    print(f"Total notional: {result.total_notional:.2f}")
    print(f"Total slippage: {result.total_slippage:.8f}")
    print(f"Total slippage %: {result.total_slippage_percent:.8f}")
    print(f"Total market impact: {result.total_market_impact:.8f}")
    print(
        f"Total market impact %: "
        f"{result.total_market_impact_percent:.8f}"
    )
    print(f"Fully filled: {result.fully_filled}")
    print(f"Slice count: {result.slice_count}")

    print("\n--- CHILD ORDER RESULTS ---")

    for fill in result.fills:
        print(
            f"Slice #{fill.sequence} | "
            f"Requested: {fill.requested_quantity:.6f} | "
            f"Filled: {fill.filled_quantity:.6f} | "
            f"Avg Price: {fill.average_execution_price:.8f} | "
            f"Slippage %: {fill.slippage_percent:.8f} | "
            f"Impact %: {fill.market_impact_percent:.8f} | "
            f"Levels: {fill.levels_consumed} | "
            f"Full: {fill.fully_filled}"
        )


def main() -> None:
    print("=" * 70)
    print("CRYPTOLAB EXECUTION SIMULATOR STRESS TEST")
    print("=" * 70)

    print("\n--- LIVE BINANCE MARKET DATA ---")

    snapshot_provider = BinanceOrderBookSnapshot()

    order_book, update_id = snapshot_provider.get_snapshot(
        symbol="BTC/USDT",
        limit=1000,
    )

    print(f"Exchange: {order_book.exchange}")
    print(f"Symbol: {order_book.symbol}")
    print(f"Snapshot update ID: {update_id}")
    print(f"Best bid: {order_book.best_bid.price}")
    print(f"Best ask: {order_book.best_ask.price}")
    print(f"Spread: {order_book.spread}")
    print(f"Spread %: {order_book.spread_percent}")
    print(f"Bid levels: {len(order_book.bids)}")
    print(f"Ask levels: {len(order_book.asks)}")

    run_scenario(
        name="BASELINE - 5 BTC",
        order_book=order_book,
        requested_quantity=5.0,
    )

    run_scenario(
        name="STRESS - 100 BTC",
        order_book=order_book,
        requested_quantity=100.0,
    )

    run_scenario(
        name="EXTREME - 500 BTC",
        order_book=order_book,
        requested_quantity=500.0,
    )

    print("\n" + "=" * 70)
    print("STRESS TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
