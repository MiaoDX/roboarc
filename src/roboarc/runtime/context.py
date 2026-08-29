"""Runtime services made available to capability adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from roboarc.contracts import EventType, ProgressSource

EmitEvent = Callable[[EventType, dict[str, Any]], Awaitable[None]]


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    """Observable services scoped to one capability invocation."""

    run_id: str
    node_id: str
    invocation_id: str
    _emit: EmitEvent

    async def report_progress(
        self,
        *,
        stage: str | None = None,
        percent: float | None = None,
        source: ProgressSource | None = None,
        message: str | None = None,
        current: float | None = None,
        total: float | None = None,
        unit: str | None = None,
    ) -> None:
        """Emit progress without inventing precision or provenance."""

        if percent is not None:
            if not 0 <= percent <= 100:
                raise ValueError("percent must be between 0 and 100")
            if source is None:
                raise ValueError("percent progress requires a source")
        elif source is not None:
            raise ValueError("progress source is only valid with percent")

        data: dict[str, Any] = {"invocation_id": self.invocation_id}
        optional = {
            "stage": stage,
            "percent": percent,
            "source": source.value if source is not None else None,
            "message": message,
            "current": current,
            "total": total,
            "unit": unit,
        }
        data.update({key: value for key, value in optional.items() if value is not None})
        await self._emit(EventType.CAPABILITY_PROGRESS, data)

    async def log(self, level: str, message: str, **fields: Any) -> None:
        """Emit a structured adapter log entry."""

        await self._emit(
            EventType.LOG,
            {
                "invocation_id": self.invocation_id,
                "level": level,
                "message": message,
                "fields": fields,
            },
        )
