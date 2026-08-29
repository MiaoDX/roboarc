from __future__ import annotations

import asyncio

import pytest

from roboarc.contracts import EventType
from roboarc.runtime.event_stream import EventStream


@pytest.mark.asyncio
async def test_subscription_replays_and_orders_events() -> None:
    stream = EventStream("run-test")
    await stream.emit(EventType.RUN_STARTED)

    observed = []

    async def consume() -> None:
        async for event in stream.subscribe(after_seq=0):
            observed.append(event)

    consumer = asyncio.create_task(consume())
    await stream.emit(EventType.LOG, {"message": "hello"})
    await stream.close()
    await consumer

    assert [event.seq for event in observed] == [1, 2]
    assert observed[1].data["message"] == "hello"
