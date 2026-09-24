from src.analysis.execution_decision import ExecutionDecision
from src.analysis.execution_planner import ExecutionPlanner
from src.analysis.risk_engine import RiskEngine


def build_decision():
    return ExecutionDecision(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp=None,
        action="BUY",
        reason="test decision",
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


def main():
    print("=" * 70)
    print("CRYPTOLAB EXECUTION PLANNER TEST")
    print("=" * 70)

    decision = build_decision()

    # ---------------------------------------------------------
    # SCENARIO 1: APPROVED 5 BTC
    # ---------------------------------------------------------
    print("\n--- SCENARIO 1: APPROVED ORDER ---")

    risk = RiskEngine()
    assessment = risk.assess(
        decision=decision,
        requested_quantity=5.0,
    )

    planner = ExecutionPlanner(
        default_slice_quantity=1.0,
        max_slices=20,
    )

    plan = planner.create_plan(
        decision=decision,
        risk_assessment=assessment,
    )

    print(f"Risk approved: {assessment.approved}")
    print(f"Requested quantity: {plan.requested_quantity}")
    print(f"Planned quantity: {plan.planned_quantity}")
    print(f"Remaining quantity: {plan.remaining_quantity}")
    print(f"Slice count: {plan.slice_count}")
    print(f"Reason: {plan.reason}")

    print("\nChild orders:")

    for execution_slice in plan.slices:
        print(
            f"  #{execution_slice.sequence} "
            f"{execution_slice.action} "
            f"{execution_slice.quantity:.6f} BTC"
        )

    # ---------------------------------------------------------
    # SCENARIO 2: RISK BLOCKS 25 BTC
    # ---------------------------------------------------------
    print("\n--- SCENARIO 2: RISK BLOCKED ORDER ---")

    risk_large = RiskEngine()

    assessment_large = risk_large.assess(
        decision=decision,
        requested_quantity=25.0,
    )

    plan_large = planner.create_plan(
        decision=decision,
        risk_assessment=assessment_large,
    )

    print(f"Risk approved: {assessment_large.approved}")
    print(f"Requested quantity: {plan_large.requested_quantity}")
    print(f"Planned quantity: {plan_large.planned_quantity}")
    print(f"Remaining quantity: {plan_large.remaining_quantity}")
    print(f"Slice count: {plan_large.slice_count}")
    print(f"Reason: {plan_large.reason}")

    # ---------------------------------------------------------
    # SCENARIO 3: LOW CONFIDENCE / NON-ACTIONABLE
    # ---------------------------------------------------------
    print("\n--- SCENARIO 3: NON-ACTIONABLE DECISION ---")

    hold_decision = ExecutionDecision(
        exchange="binance",
        symbol="BTCUSDT",
        timestamp=None,
        action="HOLD",
        reason="confidence below threshold",
        confidence=0.40,
        buy_score=0.40,
        sell_score=0.30,
        market_impact_percent=0.01,
        spread_percent=0.005,
        imbalance=0.0,
        weighted_imbalance=0.0,
        net_volume=0.0,
        cvd=0.0,
        fully_filled=True,
    )

    risk_hold = RiskEngine()

    assessment_hold = risk_hold.assess(
        decision=hold_decision,
        requested_quantity=5.0,
    )

    plan_hold = planner.create_plan(
        decision=hold_decision,
        risk_assessment=assessment_hold,
    )

    print(f"Risk approved: {assessment_hold.approved}")
    print(f"Action: {plan_hold.action}")
    print(f"Planned quantity: {plan_hold.planned_quantity}")
    print(f"Slice count: {plan_hold.slice_count}")
    print(f"Reason: {plan_hold.reason}")

    # ---------------------------------------------------------
    # ENGINE SUMMARY
    # ---------------------------------------------------------
    print("\n--- PLANNER ---")
    print(f"Scenario 1 actionable: {plan.is_actionable}")
    print(f"Scenario 1 complete: {plan.is_complete}")
    print(f"Scenario 2 actionable: {plan_large.is_actionable}")
    print(f"Scenario 3 actionable: {plan_hold.is_actionable}")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()