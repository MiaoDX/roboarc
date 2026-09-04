"""In-memory ordered event history with replayable async subscriptions."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from roboarc.contracts import EventType, RuntimeEvent


class EventStream:
    """Assign monotonic sequence numbers and retain v0.1 run history."""

    def __init__(self, run_id: str) -> None:
        self._run_id = run_id
        self._events: list[RuntimeEvent] = []
        self._closed = False
        self._condition = asyncio.Condition()

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def last_seq(self) -> int:
        return len(self._events)

    async def emit(
        self,
        event_type: EventType,
        data: dict[str, Any] | None = None,
        *,
        node_id: str | None = None,
    ) -> RuntimeEvent:
        async with self._condition:
            if self._closed:
                raise RuntimeError("cannot emit to a closed event stream")
            event = RuntimeEvent(
                seq=len(self._events) + 1,
                run_id=self._run_id,
                node_id=node_id,
                type=event_type,
                occurred_at=datetime.now(UTC),
                data=data or {},
            )
            self._events.append(event)
            self._condition.notify_all()
            return event

    def snapshot(self, after_seq: int = 0) -> tuple[RuntimeEvent, ...]:
        if after_seq < 0:
            raise ValueError("after_seq must be non-negative")
        return tuple(self._events[after_seq:])

    @property
    def history(self) -> tuple[RuntimeEvent, ...]:
        return tuple(self._events)

    async def subscribe(self, after_seq: int = 0) -> AsyncIterator[RuntimeEvent]:
        """Replay history after `after_seq`, then wait for live events until closure."""

        if after_seq < 0:
            raise ValueError("after_seq must be non-negative")
        index = after_seq
        while True:
            async with self._condition:
                def ready(index: int = index) -> bool:
                    return index < len(self._events) or self._closed

                await self._condition.wait_for(ready)
                pending = tuple(self._events[index:])
                index = len(self._events)
                closed = self._closed
            for event in pending:
                yield event
            if closed and index >= len(self._events):
                return

    async def close(self) -> None:
        async with self._condition:
            self._closed = True
            self._condition.notify_all()
