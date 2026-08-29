from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from roboarc.contracts import EventType, RuntimeEvent


def test_event_requires_timezone_and_sequence() -> None:
    event = RuntimeEvent(
        seq=1,
        run_id="run-1",
        type=EventType.RUN_STARTED,
        occurred_at=datetime.now(UTC),
    )
    assert event.seq == 1

    with pytest.raises(ValidationError, match="timezone"):
        RuntimeEvent(
            seq=1,
            run_id="run-1",
            type=EventType.RUN_STARTED,
            occurred_at=datetime.now(),
        )


def test_event_payload_must_be_json() -> None:
    with pytest.raises(ValidationError, match="JSON-serializable"):
        RuntimeEvent(
            seq=1,
            run_id="run-1",
            type=EventType.LOG,
            occurred_at=datetime.now(UTC),
            data={"bad": object()},
        )
