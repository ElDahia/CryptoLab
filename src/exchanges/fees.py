from dataclasses import dataclass


@dataclass(frozen=True)
class TradingFees:
    """
    Trading fee configuration for an exchange.

    These values are provisional research/testing values.
    Actual fees depend on account tier, volume, market type,
    maker/taker status, and exchange-specific conditions.
    """

    maker: float
    taker: float


FEES: dict[str, TradingFees] = {
    "binance": TradingFees(
        maker=0.001,
        taker=0.001,
    ),
    "okx": TradingFees(
        maker=0.001,
        taker=0.001,
    ),
    "bybit": TradingFees(
        maker=0.001,
        taker=0.001,
    ),
    "coinbase": TradingFees(
        maker=0.004,
        taker=0.004,
    ),
    "kraken": TradingFees(
        maker=0.004,
        taker=0.004,
    ),
    "gate": TradingFees(
        maker=0.002,
        taker=0.002,
    ),
    "bitget": TradingFees(
        maker=0.001,
        taker=0.001,
    ),
    "kucoin": TradingFees(
        maker=0.001,
        taker=0.001,
    ),
}