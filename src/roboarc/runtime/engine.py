"""Small, observable, in-memory Workflow IR runtime."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from roboarc.contracts import (
    CapabilityNode,
    CapabilityResult,
    ErrorCode,
    EventType,
    ExecutionError,
    NodeResult,
    NodeState,
    ResultStatus,
    RunResult,
    RunState,
    SequenceNode,
    ValidationReport,
    WaitNode,
    WorkflowDocument,
    WorkflowNode,
)
from roboarc.runtime.adapter import (
    CancellationDisposition,
    CapabilityAdapter,
    CapabilityInvocation,
)
from roboarc.runtime.context import ExecutionContext
from roboarc.runtime.event_stream import EventStream
from roboarc.runtime.registry import CapabilityRegistry
from roboarc.runtime.validation import normalize_arguments, validate_output, validate_workflow


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    cancel_grace_ms: int = 2_000

    def __post_init__(self) -> None:
        if self.cancel_grace_ms < 1:
            raise ValueError("cancel_grace_ms must be positive")


class WorkflowValidationError(ValueError):
    def __init__(self, report: ValidationReport) -> None:
        super().__init__("workflow validation failed")
        self.report = report


class RunHandle:
    """Control and observation handle for one in-memory run."""

    def __init__(self, execution: "_Execution", task: asyncio.Task[RunResult]) -> None:
        self._execution = execution
        self._task = task

    @property
    def run_id(self) -> str:
        return self._execution.run_id

    @property
    def stream(self) -> EventStream:
        return self._execution.stream

    @property
    def done(self) -> bool:
        return self._task.done()

    @property
    def state(self) -> RunState:
        if self._task.done():
            return self._task.result().state
        if self._execution.cancel_event.is_set():
            return RunState.CANCELING
        return RunState.RUNNING

    def result_if_done(self) -> RunResult | None:
        return self._task.result() if self._task.done() else None

    async def cancel(self) -> bool:
        return await self._execution.request_cancel()

    async def result(self) -> RunResult:
        return await asyncio.shield(self._task)


class Runtime:
    """Execute one adapter profile with deterministic preflight validation."""

    def __init__(
        self,
        adapter: CapabilityAdapter,
        *,
        config: RuntimeConfig | None = None,
    ) -> None:
        self.adapter = adapter
        self.registry = CapabilityRegistry.from_adapter(adapter)
        self.config = config or RuntimeConfig()
        self._runs: dict[str, RunHandle] = {}

    def validate(self, workflow: WorkflowDocument) -> ValidationReport:
        return validate_workflow(workflow, self.registry)

    async def start(self, workflow: WorkflowDocument) -> RunHandle:
        report = self.validate(workflow)
        if not report.valid:
            raise WorkflowValidationError(report)

        run_id = f"run-{uuid4().hex}"
        execution = _Execution(
            run_id=run_id,
            workflow=workflow,
            adapter=self.adapter,
            registry=self.registry,
            config=self.config,
        )
        task = asyncio.create_task(execution.run(), name=f"roboarc:{run_id}")
        handle = RunHandle(execution, task)
        self._runs[run_id] = handle
        await execution.started.wait()
        return handle

    async def run(self, workflow: WorkflowDocument) -> RunResult:
        return await (await self.start(workflow)).result()

    def get_run(self, run_id: str) -> RunHandle | None:
        return self._runs.get(run_id)

    def list_runs(self) -> tuple[RunHandle, ...]:
        return tuple(self._runs.values())

    async def shutdown(self) -> None:
        active = [handle for handle in self._runs.values() if not handle.done]
        for handle in active:
            await handle.cancel()
        if active:
            await asyncio.gather(*(handle.result() for handle in active), return_exceptions=True)


class _Execution:
    def __init__(
        self,
        *,
        run_id: str,
        workflow: WorkflowDocument,
        adapter: CapabilityAdapter,
        registry: CapabilityRegistry,
        config: RuntimeConfig,
    ) -> None:
        self.run_id = run_id
        self.workflow = workflow
        self.adapter = adapter
        self.registry = registry
        self.config = config
        self.stream = EventStream(run_id)
        self.started = asyncio.Event()
        self.cancel_event = asyncio.Event()
        self._cancel_lock = asyncio.Lock()
        self._terminal = False

    async def request_cancel(self) -> bool:
        async with self._cancel_lock:
            if self._terminal or self.cancel_event.is_set():
                return False
            self.cancel_event.set()
            await self.stream.emit(
                EventType.RUN_CANCEL_REQUESTED,
                {"state": RunState.CANCELING.value},
            )
            return True

    async def run(self) -> RunResult:
        started_at = datetime.now(UTC)
        await self.stream.emit(
            EventType.RUN_STARTED,
            {
                "workflow_id": self.workflow.id,
                "workflow_name": self.workflow.name,
                "profile_id": self.registry.profile.id,
                "state": RunState.RUNNING.value,
            },
        )
        self.started.set()
        try:
            root_result = await self._execute_node(self.workflow.workflow)
            state = _run_state_from_node(root_result.state)
            error = root_result.error
        except Exception as exc:  # defensive runtime boundary
            state = RunState.FAILED
            error = ExecutionError(
                code=ErrorCode.INTERNAL_ERROR,
                message="unhandled runtime error",
                details={"exception_type": type(exc).__name__, "message": str(exc)},
            )
            await self.stream.emit(EventType.ERROR, error.model_dump(mode="json"))

        finished_at = datetime.now(UTC)
        result = RunResult(
            run_id=self.run_id,
            workflow_id=self.workflow.id,
            state=state,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
        async with self._cancel_lock:
            self._terminal = True
        await self.stream.emit(
            EventType.RUN_FINISHED,
            {
                "state": result.state.value,
                "error": result.error.model_dump(mode="json") if result.error else None,
            },
        )
        await self.stream.close()
        return result

    async def _execute_node(self, node: WorkflowNode) -> NodeResult:
        started_at = datetime.now(UTC)
        await self.stream.emit(
            EventType.NODE_STARTED,
            {"node_type": node.type, "state": NodeState.RUNNING.value},
            node_id=node.id,
        )
        try:
            if isinstance(node, SequenceNode):
                state, output, error = await self._execute_sequence(node)
            elif isinstance(node, WaitNode):
                state, output, error = await self._execute_wait(node)
            elif isinstance(node, CapabilityNode):
                state, output, error = await self._execute_capability(node)
            else:  # pragma: no cover - discriminated schema makes this unreachable
                raise TypeError(f"unsupported node type: {type(node).__name__}")
        except Exception as exc:
            state = NodeState.FAILED
            output = {}
            error = ExecutionError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"node {node.id!r} raised an unhandled runtime error",
                details={"exception_type": type(exc).__name__, "message": str(exc)},
            )
            await self.stream.emit(
                EventType.ERROR,
                error.model_dump(mode="json"),
                node_id=node.id,
            )

        finished_at = datetime.now(UTC)
        result = NodeResult(
            node_id=node.id,
            state=state,
            output=output,
            error=error,
            started_at=started_at,
            finished_at=finished_at,
        )
        await self.stream.emit(
            EventType.NODE_FINISHED,
            {
                "node_type": node.type,
                "state": state.value,
                "output": output,
                "error": error.model_dump(mode="json") if error else None,
            },
            node_id=node.id,
        )
        return result

    async def _execute_sequence(
        self, node: SequenceNode
    ) -> tuple[NodeState, dict[str, Any], ExecutionError | None]:
        last_output: dict[str, Any] = {}
        for child in node.children:
            if self.cancel_event.is_set():
                return NodeState.CANCELED, {}, None
            result = await self._execute_node(child)
            last_output = result.output
            if result.state is not NodeState.SUCCEEDED:
                return result.state, result.output, result.error
        if self.cancel_event.is_set():
            return NodeState.CANCELED, {}, None
        return NodeState.SUCCEEDED, last_output, None

    async def _execute_wait(
        self, node: WaitNode
    ) -> tuple[NodeState, dict[str, Any], ExecutionError | None]:
        if self.cancel_event.is_set():
            return NodeState.CANCELED, {}, None
        sleep_task = asyncio.create_task(asyncio.sleep(node.duration_ms / 1000))
        cancel_task = asyncio.create_task(self.cancel_event.wait())
        try:
            done, _ = await asyncio.wait(
                {sleep_task, cancel_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancel_task in done and self.cancel_event.is_set():
                return NodeState.CANCELED, {}, None
            return NodeState.SUCCEEDED, {}, None
        finally:
            for task in (sleep_task, cancel_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(sleep_task, cancel_task, return_exceptions=True)

    async def _execute_capability(
        self, node: CapabilityNode
    ) -> tuple[NodeState, dict[str, Any], ExecutionError | None]:
        manifest = self.registry.require(node.capability)
        args = normalize_arguments(manifest, node.args)
        invocation_id = f"inv-{uuid4().hex}"

        async def emit(event_type: EventType, data: dict[str, Any]) -> None:
            await self.stream.emit(event_type, data, node_id=node.id)

        context = ExecutionContext(
            run_id=self.run_id,
            node_id=node.id,
            invocation_id=invocation_id,
            _emit=emit,
        )
        invocation = await self.adapter.invoke(node.capability, args, context)
        return await self._await_invocation(node, manifest.execution.timeout_ms, invocation)

    async def _await_invocation(
        self,
        node: CapabilityNode,
        timeout_ms: int,
        invocation: CapabilityInvocation,
    ) -> tuple[NodeState, dict[str, Any], ExecutionError | None]:
        result_task = asyncio.create_task(invocation.result())
        cancel_task = asyncio.create_task(self.cancel_event.wait())
        timeout_task = asyncio.create_task(asyncio.sleep(timeout_ms / 1000))
        detached = False
        try:
            done, _ = await asyncio.wait(
                {result_task, cancel_task, timeout_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            if result_task in done:
                return self._map_capability_result(node, result_task.result())
            if cancel_task in done and self.cancel_event.is_set():
                await self.stream.emit(
                    EventType.NODE_CANCEL_REQUESTED,
                    {"state": NodeState.CANCELING.value, "reason": "run_cancel"},
                    node_id=node.id,
                )
                disposition = await invocation.request_cancel()
                outcome = await self._wait_for_cleanup(result_task)
                if outcome is None:
                    detached = True
                    await invocation.detach()
                    return (
                        NodeState.FAILED,
                        {},
                        ExecutionError(
                            code=ErrorCode.CANCELLATION_INCOMPLETE,
                            message="capability did not reach a terminal state after cancellation",
                            details={"disposition": disposition.value},
                        ),
                    )
                return self._map_capability_result(node, outcome)

            await self.stream.emit(
                EventType.NODE_CANCEL_REQUESTED,
                {"state": NodeState.CANCELING.value, "reason": "timeout"},
                node_id=node.id,
            )
            disposition = await invocation.request_cancel()
            outcome = await self._wait_for_cleanup(result_task)
            if outcome is None:
                detached = True
                await invocation.detach()
                return (
                    NodeState.FAILED,
                    {},
                    ExecutionError(
                        code=ErrorCode.CANCELLATION_INCOMPLETE,
                        message="timed-out capability may still be executing",
                        details={"disposition": disposition.value, "timeout_ms": timeout_ms},
                    ),
                )
            return (
                NodeState.TIMED_OUT,
                {},
                ExecutionError(
                    code=ErrorCode.CAPABILITY_TIMEOUT,
                    message=f"capability exceeded its {timeout_ms} ms deadline",
                    details={
                        "disposition": disposition.value,
                        "terminal_status": outcome.status.value,
                    },
                ),
            )
        finally:
            for task in (cancel_task, timeout_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(cancel_task, timeout_task, return_exceptions=True)
            if not result_task.done() and not detached:
                result_task.cancel()
                await asyncio.gather(result_task, return_exceptions=True)

    async def _wait_for_cleanup(
        self, result_task: asyncio.Task[CapabilityResult]
    ) -> CapabilityResult | None:
        try:
            return await asyncio.wait_for(
                asyncio.shield(result_task),
                timeout=self.config.cancel_grace_ms / 1000,
            )
        except TimeoutError:
            return None

    def _map_capability_result(
        self,
        node: CapabilityNode,
        result: CapabilityResult,
    ) -> tuple[NodeState, dict[str, Any], ExecutionError | None]:
        manifest = self.registry.require(node.capability)
        if result.status is ResultStatus.SUCCESS:
            issues = validate_output(manifest, result.output, node_id=node.id)
            if issues:
                return (
                    NodeState.FAILED,
                    {},
                    ExecutionError(
                        code=ErrorCode.ADAPTER_CONTRACT_VIOLATION,
                        message="adapter returned output that violates its capability manifest",
                        details={
                            "issues": [issue.model_dump(mode="json") for issue in issues],
                        },
                    ),
                )
            return NodeState.SUCCEEDED, result.output, None
        if result.status is ResultStatus.CANCELED:
            return NodeState.CANCELED, result.output, result.error
        if result.status is ResultStatus.TIMEOUT:
            return NodeState.TIMED_OUT, result.output, result.error
        return (
            NodeState.FAILED,
            result.output,
            result.error
            or ExecutionError(
                code=ErrorCode.CAPABILITY_FAILED,
                message="capability failed without an error payload",
            ),
        )


def _run_state_from_node(state: NodeState) -> RunState:
    mapping = {
        NodeState.SUCCEEDED: RunState.SUCCEEDED,
        NodeState.FAILED: RunState.FAILED,
        NodeState.CANCELED: RunState.CANCELED,
        NodeState.TIMED_OUT: RunState.TIMED_OUT,
    }
    return mapping.get(state, RunState.FAILED)
