from dataclasses import dataclass
from datetime import datetime, timezone

from src.exchanges.base import ExchangeTradeStream


@dataclass(frozen=True)
class StreamManagerStats:
    """
    Runtime statistics for all managed exchange streams.
    """

    started_at: datetime | None
    stream_count: int
    running_count: int
    received_count: int
    processed_count: int
    error_count: int

    @property
    def is_running(self) -> bool:
        return self.running_count > 0


class ExchangeStreamManager:
    """
    Central manager for multiple exchange trade streams.

    Responsibilities:

    - Register streams
    - Start all streams
    - Stop all streams
    - Track aggregate runtime statistics
    - Expose individual streams
    """

    def __init__(
        self,
        streams: list[ExchangeTradeStream] | None = None,
    ):
        self._streams: dict[str, ExchangeTradeStream] = {}
        self._started_at: datetime | None = None

        if streams is not None:
            for stream in streams:
                self.register(stream)

    def register(
        self,
        stream: ExchangeTradeStream,
    ) -> None:
        """
        Register an exchange stream.

        Exchange names must be unique.
        """

        exchange = stream.exchange

        if exchange in self._streams:
            raise ValueError(
                f"stream already registered: {exchange}"
            )

        self._streams[exchange] = stream

    def unregister(
        self,
        exchange: str,
    ) -> ExchangeTradeStream:
        """
        Remove and return a registered stream.

        The stream must not be running.
        """

        if exchange not in self._streams:
            raise KeyError(
                f"stream not registered: {exchange}"
            )

        stream = self._streams[exchange]

        if stream.is_running:
            raise RuntimeError(
                f"cannot unregister running stream: {exchange}"
            )

        return self._streams.pop(exchange)

    def get(
        self,
        exchange: str,
    ) -> ExchangeTradeStream:
        """
        Return a registered stream by exchange name.
        """

        if exchange not in self._streams:
            raise KeyError(
                f"stream not registered: {exchange}"
            )

        return self._streams[exchange]

    @property
    def exchanges(self) -> list[str]:
        """
        Return registered exchange names.
        """

        return list(self._streams.keys())

    @property
    def stream_count(self) -> int:
        return len(self._streams)

    def start_all(self) -> None:
        """
        Start every registered stream.
        """

        if not self._streams:
            raise RuntimeError(
                "no exchange streams are registered"
            )

        if any(
            stream.is_running
            for stream in self._streams.values()
        ):
            raise RuntimeError(
                "one or more exchange streams are already running"
            )

        self._started_at = datetime.now(timezone.utc)

        started_streams = []

        try:
            for stream in self._streams.values():
                stream.start()
                started_streams.append(stream)

        except Exception:
            for started_stream in started_streams:
                try:
                    started_stream.stop()
                except Exception:
                    pass

            raise

    def stop_all(self) -> None:
        """
        Stop every registered stream.
        """

        for stream in self._streams.values():
            try:
                stream.stop()
            except Exception:
                pass

    def stats(self) -> StreamManagerStats:
        """
        Return aggregate statistics for all streams.
        """

        running_count = sum(
            1
            for stream in self._streams.values()
            if stream.is_running
        )

        received_count = sum(
            stream.received_count
            for stream in self._streams.values()
        )

        processed_count = sum(
            getattr(
                stream,
                "processed_count",
                0,
            )
            for stream in self._streams.values()
        )

        error_count = sum(
            stream.error_count
            for stream in self._streams.values()
        )

        return StreamManagerStats(
            started_at=self._started_at,
            stream_count=self.stream_count,
            running_count=running_count,
            received_count=received_count,
            processed_count=processed_count,
            error_count=error_count,
        )