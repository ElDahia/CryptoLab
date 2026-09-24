from dataclasses import dataclass

from src.exchanges.fees import FEES
from src.exchanges.snapshot import MarketSnapshot


@dataclass(frozen=True)
class ArbitrageResult:
    buy_exchange: str
    sell_exchange: str
    buy_price: float
    sell_price: float
    trade_size: float
    buy_fee: float
    sell_fee: float
    buy_cost: float
    sell_revenue: float
    net_profit: float
    net_profit_percent: float

    @property
    def is_profitable(self) -> bool:
        return self.net_profit > 0


@dataclass(frozen=True)
class ArbitrageScan:
    symbol: str
    trade_size: float
    candidate_count: int
    profitable_count: int
    best_candidate: ArbitrageResult | None
    profitable_opportunities: list[ArbitrageResult]


def calculate_net_arbitrage(
    buy_exchange: str,
    sell_exchange: str,
    buy_price: float,
    sell_price: float,
    trade_size: float = 1.0,
) -> ArbitrageResult:

    if buy_exchange not in FEES:
        raise ValueError(
            f"Unknown buy exchange: {buy_exchange}"
        )

    if sell_exchange not in FEES:
        raise ValueError(
            f"Unknown sell exchange: {sell_exchange}"
        )

    if buy_price <= 0:
        raise ValueError(
            "Buy price must be greater than zero"
        )

    if sell_price <= 0:
        raise ValueError(
            "Sell price must be greater than zero"
        )

    if trade_size <= 0:
        raise ValueError(
            "Trade size must be greater than zero"
        )

    if buy_exchange == sell_exchange:
        raise ValueError(
            "Buy and sell exchanges must be different"
        )

    buy_fee = FEES[buy_exchange].taker
    sell_fee = FEES[sell_exchange].taker

    gross_buy_cost = (
        buy_price * trade_size
    )

    gross_sell_revenue = (
        sell_price * trade_size
    )

    buy_cost = (
        gross_buy_cost
        * (1 + buy_fee)
    )

    sell_revenue = (
        gross_sell_revenue
        * (1 - sell_fee)
    )

    net_profit = (
        sell_revenue
        - buy_cost
    )

    net_profit_percent = (
        net_profit / buy_cost
    ) * 100

    return ArbitrageResult(
        buy_exchange=buy_exchange,
        sell_exchange=sell_exchange,
        buy_price=buy_price,
        sell_price=sell_price,
        trade_size=trade_size,
        buy_fee=buy_fee,
        sell_fee=sell_fee,
        buy_cost=buy_cost,
        sell_revenue=sell_revenue,
        net_profit=net_profit,
        net_profit_percent=net_profit_percent,
    )


def scan_arbitrage(
    snapshot: MarketSnapshot,
    trade_size: float = 1.0,
) -> ArbitrageScan:

    if trade_size <= 0:
        raise ValueError(
            "Trade size must be greater than zero"
        )

    candidates = []

    quotes = snapshot.quotes

    for buy_quote in quotes:
        for sell_quote in quotes:

            if (
                buy_quote.exchange
                == sell_quote.exchange
            ):
                continue

            if sell_quote.price <= buy_quote.price:
                continue

            result = calculate_net_arbitrage(
                buy_exchange=buy_quote.exchange,
                sell_exchange=sell_quote.exchange,
                buy_price=buy_quote.price,
                sell_price=sell_quote.price,
                trade_size=trade_size,
            )

            candidates.append(result)

    candidates.sort(
        key=lambda opportunity:
        opportunity.net_profit,
        reverse=True,
    )

    profitable_opportunities = [
        opportunity
        for opportunity in candidates
        if opportunity.is_profitable
    ]

    best_candidate = (
        candidates[0]
        if candidates
        else None
    )

    return ArbitrageScan(
        symbol=snapshot.symbol,
        trade_size=trade_size,
        candidate_count=len(candidates),
        profitable_count=len(
            profitable_opportunities
        ),
        best_candidate=best_candidate,
        profitable_opportunities=(
            profitable_opportunities
        ),
    )