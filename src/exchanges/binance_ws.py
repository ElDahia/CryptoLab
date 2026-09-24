import json
import threading
from datetime import datetime, timezone
from typing import Callable

import websocket

from src.analysis.microstructure import MarketTrade
from src.analysis.trade_stream import TradeStream
from src.exchanges.base import ExchangeTradeStream


class BinanceTradeWebSocket(ExchangeTradeStream):
    """
    Live Binance trade WebSocket client.

    Receives executed trades in real time and converts
    them into CryptoLab MarketTrade objects.

    The client can optionally connect directly to a
    TradeStream so incoming trades are processed
    automatically.
    """

    exchange = "binance"

    BASE_URL = "wss://stream.binance.com:9443/ws"

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        trade_stream: TradeStream | None = None,
    ):
        self.symbol = symbol

        self.exchange_symbol = (
            symbol.replace("/", "").lower()
        )

        self.url = (
            f"{self.BASE_URL}/"
            f"{self.exchange_symbol}@trade"
        )

        self.trade_stream = trade_stream

        self._socket = None
        self._thread = None
        self._running = False

        self._on_trade: Callable[
            [MarketTrade],
            None,
        ] | None = None

        self._received_count = 0
        self._processed_count = 0
        self._error_count = 0

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def received_count(self) -> int:
        return self._received_count

    @property
    def processed_count(self) -> int:
        return self._processed_count

    @property
    def error_count(self) -> int:
        return self._error_count

    def _handle_message(
        self,
        message: str,
    ) -> None:
        data = json.loads(message)

        timestamp = datetime.fromtimestamp(
            data["T"] / 1000,
            tz=timezone.utc,
        )

        trade = MarketTrade(
            exchange=self.exchange,
            symbol=self.symbol,
            price=float(data["p"]),
            quantity=float(data["q"]),
            timestamp=timestamp,
            is_buyer_maker=bool(data["m"]),
            trade_id=data["t"],
        )

        self._received_count += 1

        if self.trade_stream is not None:
            accepted = self.trade_stream.process_trade(
                trade
            )

            if accepted:
                self._processed_count += 1

        if self._on_trade is not None:
            self._on_trade(trade)

    def _on_open(
        self,
        ws,
    ) -> None:
        self._running = True

    def _on_message(
        self,
        ws,
        message: str,
    ) -> None:
        try:
            self._handle_message(message)
        except Exception:
            self._error_count += 1

    def _on_error(
        self,
        ws,
        error,
    ) -> None:
        self._error_count += 1

    def _on_close(
        self,
        ws,
        close_status_code,
        close_msg,
    ) -> None:
        self._running = False

    def start(
        self,
        on_trade: Callable[
            [MarketTrade],
            None,
        ] | None = None,
    ) -> None:
        """
        Start the Binance WebSocket.

        If a TradeStream was supplied during initialization,
        it is automatically started.
        """

        if self._running:
            raise RuntimeError(
                "Binance WebSocket is already running"
            )

        self._on_trade = on_trade

        if (
            self.trade_stream is not None
            and not self.trade_stream.is_running
        ):
            self.trade_stream.start()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )

        self._thread.start()

    def _run(self) -> None:
        self._socket = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

        self._socket.run_forever()

    def stop(self) -> None:
        """
        Stop the WebSocket and connected TradeStream.
        """

        self._running = False

        if self._socket is not None:
            self._socket.close()

        if (
            self._thread is not None
            and self._thread.is_alive()
        ):
            self._thread.join(timeout=5)

        if (
            self.trade_stream is not None
            and self.trade_stream.is_running
        ):
            self.trade_stream.stop()