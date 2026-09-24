import json
import threading
from datetime import datetime, timezone
from typing import Callable

import websocket

from src.analysis.microstructure import MarketTrade
from src.analysis.trade_stream import TradeStream
from src.exchanges.base import ExchangeTradeStream


class OKXTradeWebSocket(ExchangeTradeStream):
    """
    Live OKX public trade WebSocket client.

    Receives executed trades from the OKX trades channel
    and converts them into CryptoLab MarketTrade objects.
    """

    exchange = "okx"

    BASE_URL = "wss://ws.okx.com:8443/ws/v5/public"

    def __init__(
        self,
        symbol: str = "BTC/USDT",
        trade_stream: TradeStream | None = None,
    ):
        self.symbol = symbol

        self.exchange_symbol = symbol.replace("/", "-")

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

    def _subscribe_message(self) -> str:
        return json.dumps(
            {
                "op": "subscribe",
                "args": [
                    {
                        "channel": "trades",
                        "instId": self.exchange_symbol,
                    }
                ],
            }
        )

    def _handle_message(
        self,
        message: str,
    ) -> None:
        data = json.loads(message)

        if data.get("event") is not None:
            return

        if data.get("arg", {}).get("channel") != "trades":
            return

        for item in data.get("data", []):
            timestamp = datetime.fromtimestamp(
                int(item["ts"]) / 1000,
                tz=timezone.utc,
            )

            trade = MarketTrade(
                exchange=self.exchange,
                symbol=self.symbol,
                price=float(item["px"]),
                quantity=float(item["sz"]),
                timestamp=timestamp,
                is_buyer_maker=item["side"] == "sell",
                trade_id=item.get("tradeId"),
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

        ws.send(
            self._subscribe_message()
        )

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
        Start the OKX WebSocket.

        If a TradeStream was supplied, it is started
        automatically.
        """

        if self._running:
            raise RuntimeError(
                "OKX WebSocket is already running"
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
            self.BASE_URL,
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