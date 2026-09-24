import time

from src.analysis.adaptive_execution_engine_v5 import AdaptiveExecutionEngineV5
from src.analysis.execution_decision import ExecutionDecision
from src.analysis.risk_engine import RiskEngine
from src.analysis.v6_execution_simulation import V6ExecutionSimulation
from src.analysis.v6_live_market_feed import V6LiveMarketFeed
from src.exchanges.models import OrderBookLevel


SYMBOL = "BTC/USDT"
QUANTITY = 2.0


feed = V6LiveMarketFeed(
    symbol=SYMBOL,
    snapshot_limit=1000,
)

feed.start()

try:
    deadline = time.monotonic() + 30.0

    while time.monotonic() < deadline:
        if (
            feed.is_synchronized
            and feed.latest_order_book is not None
        ):
            break

        time.sleep(0.1)
    else:
        raise TimeoutError(
            "Timed out waiting for a synchronized V6 live book"
        )

    simulator = V6ExecutionSimulation(
        feed=feed,
        engine=AdaptiveExecutionEngineV5(
            max_slices=20,
            minimum_slice_quantity=0.01,
            max_impact_percent=0.05,
            max_spread_percent=0.02,
            impact_search_iterations=18,
            max_slice_fraction_of_liquidity=0.25,
            max_levels_per_slice=20,
        ),
    )

    live_book_before = feed.get_latest_order_book()

    private_book = simulator.snapshot_order_book()

    private_bids_before = [
        (level.price, level.quantity)
        for level in private_book.bids
    ]

    private_asks_before = [
        (level.price, level.quantity)
        for level in private_book.asks
    ]

    live_best_bid_before = live_book_before.best_bid
    live_best_ask_before = live_book_before.best_ask

    private_book.bids[0] = OrderBookLevel(
        price=private_book.bids[0].price,
        quantity=private_book.bids[0].quantity + 1000.0,
    )

    private_book.asks[0] = OrderBookLevel(
        price=private_book.asks[0].price,
        quantity=private_book.asks[0].quantity + 1000.0,
    )

    live_book_after_private_mutation = feed.get_latest_order_book()

    private_copy_is_independent = (
        live_book_after_private_mutation.best_bid
        == live_best_bid_before
        and live_book_after_private_mutation.best_ask
        == live_best_ask_before
    )

    decision = ExecutionDecision(
        exchange=live_book_after_private_mutation.exchange,
        symbol=live_book_after_private_mutation.symbol,
        timestamp=live_book_after_private_mutation.received_at,
        action="BUY",
        reason="V6 live-book simulation",
        confidence=1.0,
        buy_score=1.0,
        sell_score=0.0,
        market_impact_percent=0.0,
        spread_percent=live_book_after_private_mutation.spread_percent,
        imbalance=0.0,
        weighted_imbalance=0.0,
        net_volume=0.0,
        cvd=0.0,
        fully_filled=True,
    )

    risk = RiskEngine(
        max_order_quantity=QUANTITY,
        max_position_quantity=20.0,
        max_market_impact_percent=0.05,
        max_spread_percent=0.02,
        minimum_confidence=0.60,
        daily_loss_limit=1000.0,
    ).assess(
        decision=decision,
        requested_quantity=QUANTITY,
    )

    result = simulator.simulate(
        decision=decision,
        risk_assessment=risk,
    )

    print("V6 EXECUTION SIMULATION")
    print("Simulation only: True")
    print("Feed synchronized:", feed.is_synchronized)
    print("Requested:", result.requested_quantity)
    print("Planned:", result.planned_quantity)
    print("Filled:", result.filled_quantity)
    print("Unfilled:", result.unfilled_quantity)
    print("Average execution:", result.average_execution_price)
    print("Total notional:", result.total_notional)
    print("Slices:", result.slice_count)
    print(
        "Private snapshot independent:",
        private_copy_is_independent,
    )
    print(
        "No overfill:",
        result.filled_quantity
        <= result.planned_quantity + 1e-9,
    )
    print("Execution complete:", result.is_complete)

    assert result.requested_quantity == QUANTITY
    assert result.planned_quantity <= QUANTITY + 1e-9
    assert result.filled_quantity <= result.planned_quantity + 1e-9
    assert result.filled_quantity > 0.0
    assert result.slice_count > 0
    assert private_copy_is_independent
    assert result.is_complete

    print()
    print("VALIDATION")
    print("Requested quantity: True")
    print("Planned quantity valid: True")
    print("Filled quantity valid: True")
    print("No overfill: True")
    print("Private snapshot independent: True")
    print("Execution complete: True")

finally:
    feed.stop()
