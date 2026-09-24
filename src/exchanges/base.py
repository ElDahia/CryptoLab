from abc import ABC, abstractmethod
from typing import Callable

from src.analysis.microstructure import MarketTrade


class ExchangeAdapter(ABC):
    """
    Base interface for CryptoLab exchange adapters.
    """

    name: str

    @abstractmethod
    def get_price(
        self,
        symbol: str = "BTC/USDT",
    ) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_order_book(
        self,
        symbol: str = "BTC/USDT",
        limit: int = 5,
    ):
        raise NotImplementedError


class ExchangeTradeStream(ABC):
    """
    Base interface for real-time trade streams.

    Every exchange WebSocket implementation should expose
    the same lifecycle and callback interface.
    """

    exchange: str

    @abstractmethod
    def start(
        self,
        on_trade: Callable[[MarketTrade], None] | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def is_running(self) -> bool:
        raise NotImplementedError

    @property
    @abstractmethod
    def received_count(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def error_count(self) -> int:
        raise NotImplementedError