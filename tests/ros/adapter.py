from __future__ import annotations

import asyncio
import json
import threading
from concurrent.futures import Future
from typing import Any

import rclpy
from example_interfaces.action import Fibonacci
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node

from roboarc.contracts import (
    CapabilityManifest,
    CapabilityRef,
    CapabilityResult,
    ErrorCode,
    ExecutionError,
    ExecutionTraits,
    ProgressMode,
    ProgressSource,
    ProgressSpec,
    ResultStatus,
    RobotProfile,
    ValueSpec,
    ValueType,
)
from roboarc.runtime.adapter import CancellationDisposition, CapabilityInvocation
from roboarc.runtime.context import ExecutionContext


class RosActionAdapter:
    capability = CapabilityManifest(
        id="demo.ros_fibonacci",
        version=1,
        title="ROS Fibonacci Action",
        category="Demo",
        inputs={"order": ValueSpec(type=ValueType.INTEGER, required=True)},
        outputs={"sequence": ValueSpec(type=ValueType.STRING, required=True)},
        execution=ExecutionTraits(timeout_ms=500, cancellable=True),
        progress=ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.NATIVE),
    )

    def __init__(self, action_name: str = "roboarc/fibonacci", *, timeout_ms: int = 500) -> None:
        if not rclpy.ok():
            rclpy.init()
        self._node = Node("roboarc_action_adapter")
        self._client = ActionClient(self._node, Fibonacci, action_name)
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()
        self._manifest = self.capability.model_copy(
            update={"execution": ExecutionTraits(timeout_ms=timeout_ms, cancellable=True)}
        )

    @property
    def profile(self) -> RobotProfile:
        return RobotProfile(
            id="ros-test",
            title="ROS test robot",
            adapter="ros-test",
            capabilities=(self._manifest.ref,),
        )

    @property
    def manifests(self) -> tuple[CapabilityManifest, ...]:
        return (self._manifest,)

    async def invoke(
        self, capability: CapabilityRef, args: dict[str, object], context: ExecutionContext
    ) -> CapabilityInvocation:
        if capability != self._manifest.ref:
            raise KeyError(capability.id)
        try:
            available = await asyncio.to_thread(self._client.wait_for_server, 0.2)
        except Exception as exc:
            return _transport_error(exc)
        if not available:
            return _ImmediateInvocation(
                CapabilityResult(
                    status=ResultStatus.FAILURE,
                    error=ExecutionError(
                        code=ErrorCode.CAPABILITY_FAILED,
                        message="ROS action server unavailable",
                        details={"ros_status": "server_unavailable"},
                    ),
                )
            )
        goal = Fibonacci.Goal(order=int(args["order"]))
        loop = asyncio.get_running_loop()

        def feedback(msg: Any) -> None:
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    context.report_progress(
                        percent=min(100, 100 * len(msg.feedback.sequence) / max(1, goal.order)),
                        source=ProgressSource.NATIVE,
                        current=len(msg.feedback.sequence),
                        total=goal.order,
                        unit="item",
                    )
                )
            )

        try:
            future = self._client.send_goal_async(goal, feedback_callback=feedback)
            handle = await asyncio.wrap_future(_to_concurrent(future))
        except Exception as exc:
            return _transport_error(exc)
        if not handle.accepted:
            return _ImmediateInvocation(
                CapabilityResult(
                    status=ResultStatus.FAILURE,
                    error=ExecutionError(
                        code=ErrorCode.CAPABILITY_FAILED,
                        message="ROS goal rejected",
                        details={"ros_status": "rejected"},
                    ),
                )
            )
        return RosInvocation(handle, goal.order)

    async def close(self) -> None:
        self._executor.shutdown()
        self._node.destroy_node()
        self._thread.join(timeout=2)
        if self._thread.is_alive():
            raise RuntimeError("ROS adapter executor thread did not terminate")
        if rclpy.ok():
            rclpy.shutdown()


def _to_concurrent(future: Any) -> Future[Any]:
    result: Future[Any] = Future()

    def complete(done: Any) -> None:
        if result.done():
            return
        exception = done.exception()
        if exception is None:
            result.set_result(done.result())
        else:
            result.set_exception(exception)

    future.add_done_callback(complete)
    return result


def _transport_error(exc: Exception) -> _ImmediateInvocation:
    return _ImmediateInvocation(
        CapabilityResult(
            status=ResultStatus.FAILURE,
            error=ExecutionError(
                code=ErrorCode.CAPABILITY_FAILED,
                message="ROS action transport error",
                details={
                    "ros_status": "transport_error",
                    "message": str(exc),
                },
            ),
        )
    )


class RosInvocation(CapabilityInvocation):
    def __init__(self, handle: Any, order: int) -> None:
        self._handle, self._order = handle, order
        self._result: asyncio.Task[CapabilityResult] | None = None

    async def result(self) -> CapabilityResult:
        if self._result is None:

            async def wait_result() -> CapabilityResult:
                response = await asyncio.wrap_future(
                    _to_concurrent(self._handle.get_result_async())
                )
                status = int(response.status)
                if status == 5:
                    return CapabilityResult(status=ResultStatus.CANCELED, error=None)
                if status == 6:
                    return CapabilityResult(
                        status=ResultStatus.FAILURE,
                        error=ExecutionError(
                            code=ErrorCode.CAPABILITY_FAILED,
                            message="ROS action aborted",
                            details={"ros_status": "aborted"},
                        ),
                    )
                return CapabilityResult(
                    status=ResultStatus.SUCCESS,
                    output={"sequence": json.dumps(list(response.result.sequence))},
                )

            self._result = asyncio.create_task(wait_result())
        return await asyncio.shield(self._result)

    async def request_cancel(self) -> CancellationDisposition:
        if self._result is not None and self._result.done():
            return CancellationDisposition.ALREADY_COMPLETE
        response = await asyncio.wrap_future(_to_concurrent(self._handle.cancel_goal_async()))
        if response.goals_canceling:
            return CancellationDisposition.ACCEPTED
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        if self._result is not None and not self._result.done():
            self._result.cancel()
            await asyncio.gather(self._result, return_exceptions=True)


class _ImmediateInvocation(CapabilityInvocation):
    def __init__(self, result: CapabilityResult) -> None:
        self._value = result

    async def result(self) -> CapabilityResult:
        return self._value

    async def request_cancel(self) -> CancellationDisposition:
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        return None
