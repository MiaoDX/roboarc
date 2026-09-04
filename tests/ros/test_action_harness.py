from __future__ import annotations

import asyncio
import threading
import time

import pytest

pytest.importorskip("rclpy", reason="ROS 2 Jazzy is required for ROS integration tests")

import rclpy
from example_interfaces.action import Fibonacci
from rclpy.action import ActionClient, ActionServer, CancelResponse, GoalResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node

from roboarc.contracts import EventType, ProgressSource, RunState, WorkflowDocument
from roboarc.runtime import Runtime, RuntimeConfig

from .adapter import RosActionAdapter


class FibonacciServer(Node):
    """Deterministic action server used by the repository-local proof lane."""

    def __init__(self) -> None:
        super().__init__("roboarc_fibonacci_server")
        self.mode = "success"
        self.delay_s = 0.0
        self._server = ActionServer(
            self,
            Fibonacci,
            "roboarc/fibonacci",
            self.execute,
            callback_group=ReentrantCallbackGroup(),
            cancel_callback=lambda _: CancelResponse.ACCEPT,
            goal_callback=lambda _: (
                GoalResponse.REJECT if self.mode == "reject" else GoalResponse.ACCEPT
            ),
        )

    def execute(self, goal_handle):
        sequence = [0, 1]
        order = max(0, int(goal_handle.request.order))
        for _ in range(2, order + 1):
            if self.delay_s:
                time.sleep(self.delay_s)
            if goal_handle.is_cancel_requested and self.mode != "ignore_cancel":
                goal_handle.canceled()
                return Fibonacci.Result(sequence=sequence)
            sequence.append(sequence[-1] + sequence[-2])
            goal_handle.publish_feedback(Fibonacci.Feedback(sequence=sequence))
        if self.mode == "abort":
            goal_handle.abort()
        else:
            goal_handle.succeed()
        return Fibonacci.Result(sequence=sequence)

    def destroy_node(self) -> bool:
        self._server.destroy()
        return super().destroy_node()


def test_direct_action_server_client_smoke() -> None:
    rclpy.init()
    server = FibonacciServer()
    client_node = Node("roboarc_fibonacci_client")
    client = ActionClient(client_node, Fibonacci, "roboarc/fibonacci")
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    executor.add_node(client_node)
    try:
        assert client.wait_for_server(timeout_sec=2.0)
        future = client.send_goal_async(Fibonacci.Goal(order=5))
        while not future.done():
            executor.spin_once(timeout_sec=0.05)
        handle = future.result()
        assert handle.accepted
        result_future = handle.get_result_async()
        while not result_future.done():
            executor.spin_once(timeout_sec=0.05)
        assert list(result_future.result().result.sequence) == [0, 1, 1, 2, 3, 5]
    finally:
        executor.shutdown()
        client_node.destroy_node()
        server.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


@pytest.mark.asyncio
async def test_workflow_runtime_reaches_ros_action_result() -> None:
    rclpy.init()
    server = FibonacciServer()
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter()
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-proof",
            "name": "ROS proof",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 5},
            },
        }
    )
    try:
        handle = await Runtime(adapter).start(workflow)
        result = await handle.result()
        assert result.state is RunState.SUCCEEDED
        finished = next(
            event
            for event in reversed(handle.stream.snapshot())
            if event.type is EventType.NODE_FINISHED
        )
        assert finished.data["output"]["sequence"] == "[0, 1, 1, 2, 3, 5]"
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()


@pytest.mark.asyncio
async def test_ros_abort_and_unavailable_are_failures() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.mode = "abort"
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter()
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-fail",
            "name": "ROS fail",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 3},
            },
        }
    )
    try:
        result = await Runtime(adapter).run(workflow)
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.details["ros_status"] == "aborted"
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()

    rclpy.init()
    unavailable = RosActionAdapter("roboarc/missing")
    try:
        result = await Runtime(unavailable).run(workflow)
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.details["ros_status"] == "server_unavailable"
    finally:
        await unavailable.close()


@pytest.mark.asyncio
async def test_native_progress_and_cancellation_are_truthful() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.delay_s = 0.02
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter()
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-cancel",
            "name": "ROS cancellation",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 20},
            },
        }
    )
    try:
        handle = await Runtime(adapter).start(workflow)
        while not any(
            event.type is EventType.CAPABILITY_PROGRESS for event in handle.stream.snapshot()
        ):
            await asyncio.sleep(0.005)
        assert await handle.cancel()
        result = await handle.result()
        assert result.state is RunState.CANCELED
        events = handle.stream.snapshot()
        progress = [e for e in events if e.type is EventType.CAPABILITY_PROGRESS]
        assert progress
        assert all(e.data["source"] == ProgressSource.NATIVE.value for e in progress)
        assert [e.seq for e in events] == list(range(1, len(events) + 1))
        cancel_seq = next(e.seq for e in events if e.type is EventType.RUN_CANCEL_REQUESTED)
        finished_seq = next(e.seq for e in events if e.type is EventType.RUN_FINISHED)
        assert cancel_seq < finished_seq
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()


@pytest.mark.asyncio
async def test_timeout_reports_native_terminal_cancellation() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.delay_s = 0.03
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter(timeout_ms=20)
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-timeout",
            "name": "ROS timeout",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 20},
            },
        }
    )
    try:
        result = await Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=500)).run(workflow)
        assert result.state is RunState.TIMED_OUT
        assert result.error is not None
        assert result.error.details["terminal_status"] == "canceled"
        assert result.error.details["disposition"] == "accepted"
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()


@pytest.mark.asyncio
async def test_rejection_and_transport_exception_are_stable_failures() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.mode = "reject"
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-reject",
            "name": "ROS rejection",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 5},
            },
        }
    )
    adapter = RosActionAdapter()
    try:
        result = await Runtime(adapter).run(workflow)
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.details["ros_status"] == "rejected"
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()

    rclpy.init()
    broken = RosActionAdapter()
    broken._client.destroy()
    try:
        result = await Runtime(broken).run(workflow)
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.details["ros_status"] == "transport_error"
        assert isinstance(result.error.details["message"], str)
    finally:
        await broken.close()


@pytest.mark.asyncio
async def test_accepted_but_nonterminal_cancel_is_incomplete() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.mode = "ignore_cancel"
    server.delay_s = 0.02
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter()
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-incomplete",
            "name": "ROS incomplete cancellation",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 30},
            },
        }
    )
    try:
        handle = await Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=5)).start(workflow)
        while not any(e.type is EventType.CAPABILITY_PROGRESS for e in handle.stream.snapshot()):
            await asyncio.sleep(0.005)
        assert await handle.cancel()
        result = await handle.result()
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.code.value == "cancellation_incomplete"
        assert result.error.details["disposition"] == "accepted"
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()


@pytest.mark.asyncio
async def test_timeout_grace_expiry_is_cancellation_incomplete() -> None:
    rclpy.init()
    server = FibonacciServer()
    server.mode = "ignore_cancel"
    server.delay_s = 0.02
    executor = MultiThreadedExecutor(num_threads=2)
    executor.add_node(server)
    thread = threading.Thread(target=executor.spin, daemon=True)
    thread.start()
    adapter = RosActionAdapter(timeout_ms=10)
    workflow = WorkflowDocument.model_validate(
        {
            "workflow_schema_version": 1,
            "id": "ros-timeout-incomplete",
            "name": "ROS timeout incomplete",
            "workflow": {
                "id": "fib",
                "type": "capability",
                "capability": {"id": "demo.ros_fibonacci", "version": 1},
                "args": {"order": 30},
            },
        }
    )
    try:
        result = await Runtime(adapter, config=RuntimeConfig(cancel_grace_ms=5)).run(workflow)
        assert result.state is RunState.FAILED
        assert result.error is not None
        assert result.error.code.value == "cancellation_incomplete"
        assert result.error.details == {
            "disposition": "accepted",
            "timeout_ms": 10,
        }
    finally:
        await adapter.close()
        executor.shutdown()
        server.destroy_node()
        thread.join(timeout=2)
        assert not thread.is_alive()
        if rclpy.ok():
            rclpy.shutdown()
