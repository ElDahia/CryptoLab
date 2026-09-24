from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.execution_simulator import ExecutionSimulationResult
from src.exchanges.fees import FEES


@dataclass(frozen=True)
class ExecutionCostResult:
    exchange: str
    symbol: str
    action: str

    requested_quantity: float
    filled_quantity: float
    unfilled_quantity: float

    reference_price: float
    average_execution_price: float

    gross_notional: float
    trading_fee: float

    price_shortfall: float
    market_impact_cost: float

    total_execution_cost: float
    total_execution_cost_percent: float

    implementation_shortfall: float
    implementation_shortfall_percent: float

    fully_filled: bool
    calculated_at: datetime

    @property
    def fill_ratio(self) -> float:
        if self.requested_quantity <= 0:
            return 0.0

        return self.filled_quantity / self.requested_quantity


class ExecutionCostEngine:
    """
    Research-grade execution cost calculator.

    Cost model:

        Trading Fee
             +
        Price Shortfall
             +
        Market Impact
             =
        Total Execution Cost

    Implementation Shortfall represents the price-based execution
    loss relative to the reference price.

    This component is research/simulation only.
    It does NOT place real orders.
    """

    EPSILON = 1e-12

    def calculate(
        self,
        simulation: ExecutionSimulationResult,
    ) -> ExecutionCostResult:

        if simulation.exchange not in FEES:
            raise ValueError(
                f"No fee configuration found for exchange: "
                f"{simulation.exchange}"
            )

        if simulation.action not in {"BUY", "SELL"}:
            raise ValueError(
                "Simulation action must be BUY or SELL"
            )

        if simulation.filled_quantity <= self.EPSILON:
            return ExecutionCostResult(
                exchange=simulation.exchange,
                symbol=simulation.symbol,
                action=simulation.action,
                requested_quantity=simulation.requested_quantity,
                filled_quantity=0.0,
                unfilled_quantity=simulation.unfilled_quantity,
                reference_price=0.0,
                average_execution_price=0.0,
                gross_notional=0.0,
                trading_fee=0.0,
                price_shortfall=0.0,
                market_impact_cost=0.0,
                total_execution_cost=0.0,
                total_execution_cost_percent=0.0,
                implementation_shortfall=0.0,
                implementation_shortfall_percent=0.0,
                fully_filled=simulation.fully_filled,
                calculated_at=datetime.now(timezone.utc),
            )

        if not simulation.fills:
            raise ValueError(
                "Simulation contains filled quantity but no fills"
            )

        reference_price = simulation.fills[0].reference_price

        average_execution_price = simulation.average_execution_price
        filled_quantity = simulation.filled_quantity
        gross_notional = simulation.total_notional

        if reference_price <= self.EPSILON:
            raise ValueError(
                "Reference price must be greater than zero"
            )

        if average_execution_price <= self.EPSILON:
            raise ValueError(
                "Average execution price must be greater than zero"
            )

        # ---------------------------------------------------------
        # Trading fee
        # ---------------------------------------------------------

        fee_rate = FEES[simulation.exchange].taker

        trading_fee = gross_notional * fee_rate

        # ---------------------------------------------------------
        # Implementation shortfall
        #
        # BUY:
        #     execution above reference = cost
        #
        # SELL:
        #     execution below reference = cost
        # ---------------------------------------------------------

        if simulation.action == "BUY":
            implementation_shortfall = (
                average_execution_price
                - reference_price
            ) * filled_quantity

        else:
            implementation_shortfall = (
                reference_price
                - average_execution_price
            ) * filled_quantity

        implementation_shortfall = max(
            0.0,
            implementation_shortfall,
        )

        # ---------------------------------------------------------
        # Price shortfall is the same economic quantity as
        # implementation shortfall.
        #
        # We expose both names for reporting clarity, but only
        # count it ONCE in total execution cost.
        # ---------------------------------------------------------

        price_shortfall = implementation_shortfall

        # ---------------------------------------------------------
        # Market impact
        #
        # The simulator already calculates impact as a price
        # difference. Convert that impact into monetary cost.
        # ---------------------------------------------------------

        market_impact_cost = (
            simulation.total_market_impact
            * filled_quantity
        )

        market_impact_cost = max(
            0.0,
            market_impact_cost,
        )

        # ---------------------------------------------------------
        # Total cost
        #
        # IMPORTANT:
        # implementation shortfall / price shortfall is counted
        # once only.
        # ---------------------------------------------------------

        total_execution_cost = (
            trading_fee
            + price_shortfall
            + market_impact_cost
        )

        if gross_notional > self.EPSILON:
            total_execution_cost_percent = (
                total_execution_cost
                / gross_notional
            ) * 100.0
        else:
            total_execution_cost_percent = 0.0

        # ---------------------------------------------------------
        # Shortfall percentage
        # ---------------------------------------------------------

        reference_notional = (
            reference_price
            * filled_quantity
        )

        if reference_notional > self.EPSILON:
            implementation_shortfall_percent = (
                implementation_shortfall
                / reference_notional
            ) * 100.0
        else:
            implementation_shortfall_percent = 0.0

        return ExecutionCostResult(
            exchange=simulation.exchange,
            symbol=simulation.symbol,
            action=simulation.action,
            requested_quantity=simulation.requested_quantity,
            filled_quantity=filled_quantity,
            unfilled_quantity=simulation.unfilled_quantity,
            reference_price=reference_price,
            average_execution_price=average_execution_price,
            gross_notional=gross_notional,
            trading_fee=trading_fee,
            price_shortfall=price_shortfall,
            market_impact_cost=market_impact_cost,
            total_execution_cost=total_execution_cost,
            total_execution_cost_percent=total_execution_cost_percent,
            implementation_shortfall=implementation_shortfall,
            implementation_shortfall_percent=implementation_shortfall_percent,
            fully_filled=simulation.fully_filled,
            calculated_at=datetime.now(timezone.utc),
        )
