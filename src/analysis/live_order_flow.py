from dataclasses import dataclass
from datetime import datetime, timezone

from src.analysis.microstructure import MarketTrade


@dataclass(frozen=True)
class LiveOrderFlowState:
    """
    Latest live order-flow state for one market.
    """

    exchange: str
    symbol: str
    timestamp: datetime

    trade_count: int

    buy_volume: float
    sell_volume: float

    buy_notional: float
    sell_notional: float

    net_volume: float
    net_notional: float

    buy_ratio: float
    sell_ratio: float

    cvd: float

    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume

    @property
    def total_notional(self) -> float:
        return self.buy_notional + self.sell_notional

    @property
    def delta(self) -> float:
        return self.net_volume

    @property
    def delta_notional(self) -> float:
        return self.net_notional

    def age_seconds(self) -> float:
        return (
            datetime.now(timezone.utc) - self.timestamp
        ).total_seconds()

    def is_fresh(
        self,
        max_age_seconds: float = 5.0,
    ) -> bool:
        return self.age_seconds() <= max_age_seconds


class LiveOrderFlowEngine:
    """
    Maintains live executed-trade flow and cumulative
    volume delta (CVD) for one market.
    """

    def __init__(
        self,
        exchange: str,
        symbol: str,
    ):
        self.exchange = exchange
        self.symbol = symbol

        self._trade_count = 0

        self._buy_volume = 0.0
        self._sell_volume = 0.0

        self._buy_notional = 0.0
        self._sell_notional = 0.0

        self._cvd = 0.0

        self._latest_state: (
            LiveOrderFlowState | None
        ) = None

    @property
    def latest_state(
        self,
    ) -> LiveOrderFlowState | None:
        return self._latest_state

    @property
    def trade_count(self) -> int:
        return self._trade_count

    @property
    def cvd(self) -> float:
        return self._cvd

    def update(
        self,
        trade: MarketTrade,
    ) -> LiveOrderFlowState:
        """
        Process one normalized market trade.
        """

        if trade.exchange != self.exchange:
            raise ValueError(
                "trade exchange does not match engine"
            )

        if trade.symbol != self.symbol:
            raise ValueError(
                "trade symbol does not match engine"
            )

        self._trade_count += 1

        if trade.is_buyer_maker:
            self._sell_volume += trade.quantity
            self._sell_notional += trade.notional

            self._cvd -= trade.quantity

        else:
            self._buy_volume += trade.quantity
            self._buy_notional += trade.notional

            self._cvd += trade.quantity

        net_volume = (
            self._buy_volume
            - self._sell_volume
        )

        net_notional = (
            self._buy_notional
            - self._sell_notional
        )

        total_volume = (
            self._buy_volume
            + self._sell_volume
        )

        if total_volume == 0:
            buy_ratio = 0.0
            sell_ratio = 0.0

        else:
            buy_ratio = (
                self._buy_volume
                / total_volume
            )

            sell_ratio = (
                self._sell_volume
                / total_volume
            )

        state = LiveOrderFlowState(
            exchange=trade.exchange,
            symbol=trade.symbol,
            timestamp=trade.timestamp,
            trade_count=self._trade_count,
            buy_volume=self._buy_volume,
            sell_volume=self._sell_volume,
            buy_notional=self._buy_notional,
            sell_notional=self._sell_notional,
            net_volume=net_volume,
            net_notional=net_notional,
            buy_ratio=buy_ratio,
            sell_ratio=sell_ratio,
            cvd=self._cvd,
        )

        self._latest_state = state

        return state

    def reset(self) -> None:
        """
        Reset the accumulated live order flow.
        """

        self._trade_count = 0

        self._buy_volume = 0.0
        self._sell_volume = 0.0

        self._buy_notional = 0.0
        self._sell_notional = 0.0

        self._cvd = 0.0

        self._latest_state = None