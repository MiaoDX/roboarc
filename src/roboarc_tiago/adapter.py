"""ROS 2 Jazzy adapter for the optional TIAGo integration lane."""

from __future__ import annotations

import asyncio
import math
import threading
from concurrent.futures import Future
from datetime import UTC, datetime
from typing import Any, cast

import rclpy
from action_msgs.msg import GoalStatus
from control_msgs.action import FollowJointTrajectory
from geometry_msgs.msg import PoseStamped, TwistStamped
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from std_msgs.msg import String
from tf2_ros import Buffer, TransformException, TransformListener
from trajectory_msgs.msg import JointTrajectoryPoint

from roboarc.contracts import (
    CapabilityRef,
    CapabilityResult,
    ErrorCode,
    ExecutionError,
    ProgressSource,
    ResultStatus,
)
from roboarc.runtime.adapter import (
    CancellationDisposition,
    CapabilityAdapter,
    CapabilityInvocation,
)
from roboarc.runtime.context import ExecutionContext
from roboarc.telemetry import ActionPhase, ActionState, Observation

from .profile import (
    DEFAULT_LOCATIONS,
    GOTO_LOCATION,
    LOOK_AT,
    SAY,
    STOP_NAVIGATION,
    TIAGO_MANIFESTS,
    TIAGO_PROFILE,
    NamedLocation,
)
from .telemetry_bridge import (
    estimated_distance_observation,
    pose_observations,
    ros_timestamp,
)


class TiagoRosAdapter(CapabilityAdapter):
    """Translate RoboArc capabilities to the standard TIAGo ROS interfaces."""

    def __init__(
        self,
        *,
        locations: dict[str, NamedLocation] | None = None,
        navigate_action: str = "navigate_to_pose",
        head_action: str = "head_controller/follow_joint_trajectory",
        speech_topic: str = "roboarc/speech",
        cmd_vel_topic: str = "mobile_base_controller/cmd_vel",
        server_timeout_s: float = 5.0,
    ) -> None:
        if not rclpy.ok():
            rclpy.init()
        self._node = Node("roboarc_tiago_adapter")
        self._navigate = ActionClient(self._node, NavigateToPose, navigate_action)
        self._head = ActionClient(self._node, FollowJointTrajectory, head_action)
        self._speech = self._node.create_publisher(String, speech_topic, 10)
        self._cmd_vel = self._node.create_publisher(TwistStamped, cmd_vel_topic, 10)
        self._tf_buffer = Buffer()
        self._tf_listener = TransformListener(self._tf_buffer, self._node)
        self._executor = SingleThreadedExecutor()
        self._executor.add_node(self._node)
        self._thread = threading.Thread(target=self._executor.spin, daemon=True)
        self._thread.start()
        self._locations = dict(locations or DEFAULT_LOCATIONS)
        self._server_timeout_s = server_timeout_s
        self._telemetry: list[Observation] = []
        self._active_navigation: Any | None = None

    @property
    def profile(self):
        return TIAGO_PROFILE

    @property
    def manifests(self):
        return TIAGO_MANIFESTS

    @property
    def telemetry(self) -> tuple[Observation, ...]:
        return tuple(self._telemetry)

    async def invoke(
        self,
        capability: CapabilityRef,
        args: dict[str, object],
        context: ExecutionContext,
    ) -> CapabilityInvocation:
        if capability == GOTO_LOCATION.ref:
            return await self._goto_location(args, context)
        if capability == STOP_NAVIGATION.ref:
            return await self._stop_navigation(context)
        if capability == LOOK_AT.ref:
            return await self._look_at(args, context)
        if capability == SAY.ref:
            self._speech.publish(String(data=str(args["text"])))
            await context.report_progress(stage="published", message="Speech text published")
            return _ImmediateInvocation(CapabilityResult(status=ResultStatus.SUCCESS))
        raise KeyError(f"unsupported TIAGo capability: {capability.id}@{capability.version}")

    async def _goto_location(
        self, args: dict[str, object], context: ExecutionContext
    ) -> CapabilityInvocation:
        target_name = str(args["target"])
        target = self._locations.get(target_name)
        if target is None:
            return _failure("unknown_location", f"Unknown TIAGo location: {target_name}")
        if not await asyncio.to_thread(self._navigate.wait_for_server, self._server_timeout_s):
            return _failure("server_unavailable", "Nav2 NavigateToPose server unavailable")

        goal = NavigateToPose.Goal()
        goal.pose = _pose_stamped(self._node, "map", target)
        loop = asyncio.get_running_loop()
        initial_distance: list[float | None] = [None]

        def feedback(message: Any) -> None:
            feedback_value = message.feedback
            remaining = max(0.0, float(feedback_value.distance_remaining))
            if initial_distance[0] is None:
                initial_distance[0] = max(remaining, 1e-12)
            timestamp = _message_time(feedback_value.current_pose)
            loop.call_soon_threadsafe(
                lambda: asyncio.create_task(
                    context.report_progress(
                        stage="navigating",
                        percent=max(
                            0.0,
                            min(
                                100.0,
                                100.0 * (initial_distance[0] - remaining) / initial_distance[0],
                            ),
                        ),
                        source=ProgressSource.ESTIMATED,
                        current=max(0.0, initial_distance[0] - remaining),
                        total=initial_distance[0],
                        unit="m",
                    )
                )
            )
            self._record_navigation_feedback(
                context, feedback_value.current_pose, remaining, initial_distance[0], timestamp
            )

        self._record_action(context, GOTO_LOCATION.id, ActionPhase.PENDING)
        handle = await _await_ros(self._navigate.send_goal_async(goal, feedback_callback=feedback))
        if not handle.accepted:
            self._record_action(context, GOTO_LOCATION.id, ActionPhase.FAILED, "goal rejected")
            return _failure("rejected", "Nav2 goal rejected")
        self._active_navigation = handle
        self._record_action(context, GOTO_LOCATION.id, ActionPhase.ACCEPTED)
        self._record_action(context, GOTO_LOCATION.id, ActionPhase.EXECUTING)
        return _RosActionInvocation(
            handle,
            context=context,
            action_id=GOTO_LOCATION.id,
            output={"target": target_name},
            on_terminal=self._navigation_terminal,
            record_action=self._record_action,
        )

    async def _stop_navigation(self, context: ExecutionContext) -> CapabilityInvocation:
        stop = TwistStamped()
        stop.header.stamp = self._node.get_clock().now().to_msg()
        self._cmd_vel.publish(stop)
        handle = self._active_navigation
        if handle is None:
            await context.report_progress(stage="idle", message="No active Nav2 goal")
            return _ImmediateInvocation(CapabilityResult(status=ResultStatus.SUCCESS))
        response = await _await_ros(handle.cancel_goal_async())
        if not response.goals_canceling:
            return _failure("cancel_not_confirmed", "Nav2 did not accept the stop request")
        await context.report_progress(stage="cancel_accepted", message="Nav2 accepted stop request")
        return _ImmediateInvocation(CapabilityResult(status=ResultStatus.SUCCESS))

    async def _look_at(
        self, args: dict[str, object], context: ExecutionContext
    ) -> CapabilityInvocation:
        if not await asyncio.to_thread(self._head.wait_for_server, self._server_timeout_s):
            return _failure("server_unavailable", "Head trajectory action server unavailable")
        frame = str(args["frame"])
        target = (
            float(cast(float | int, args["x"])),
            float(cast(float | int, args["y"])),
            float(cast(float | int, args["z"])),
        )
        try:
            pan, tilt = self._head_angles(frame, target)
        except TransformException as error:
            return _failure("transform_unavailable", str(error))
        goal = FollowJointTrajectory.Goal()
        goal.trajectory.joint_names = ["head_1_joint", "head_2_joint"]
        point = JointTrajectoryPoint(positions=[pan, tilt])
        point.time_from_start.sec = 2
        goal.trajectory.points = [point]
        self._record_action(context, LOOK_AT.id, ActionPhase.PENDING)
        handle = await _await_ros(self._head.send_goal_async(goal))
        if not handle.accepted:
            self._record_action(context, LOOK_AT.id, ActionPhase.FAILED, "goal rejected")
            return _failure("rejected", "Head trajectory goal rejected")
        self._record_action(context, LOOK_AT.id, ActionPhase.ACCEPTED)
        self._record_action(context, LOOK_AT.id, ActionPhase.EXECUTING)
        await context.report_progress(stage="looking", message="Head trajectory accepted")
        return _RosActionInvocation(
            handle,
            context=context,
            action_id=LOOK_AT.id,
            output={},
            record_action=self._record_action,
        )

    def _head_angles(
        self, frame: str, target: tuple[float, float, float]
    ) -> tuple[float, float]:
        target_base = target
        if frame != "base_footprint":
            transform = self._tf_buffer.lookup_transform(
                "base_footprint", frame, rclpy.time.Time()
            )
            target_base = _transform_point(transform, target)
        head = self._tf_buffer.lookup_transform(
            "base_footprint", "head_2_link", rclpy.time.Time()
        ).transform.translation
        dx = target_base[0] - head.x
        dy = target_base[1] - head.y
        dz = target_base[2] - head.z
        pan = _clamp(math.atan2(dy, dx), math.radians(-75), math.radians(75))
        tilt = _clamp(
            -math.atan2(dz, math.hypot(dx, dy)),
            math.radians(-60),
            math.radians(45),
        )
        return pan, tilt

    def _record_navigation_feedback(
        self,
        context: ExecutionContext,
        current_pose: Any,
        remaining: float,
        initial: float,
        timestamp: datetime,
    ) -> None:
        self._telemetry.append(
            estimated_distance_observation(
                timestamp=timestamp,
                run_id=context.run_id,
                node_id=context.node_id,
                invocation_id=context.invocation_id,
                remaining=remaining,
                initial=initial,
            )
        )
        pose = current_pose.pose
        frame_id = current_pose.header.frame_id or "map"
        try:
            transform = self._tf_buffer.lookup_transform("map", "base_footprint", rclpy.time.Time())
        except TransformException:
            values = (
                frame_id,
                (pose.position.x, pose.position.y, pose.position.z),
                (pose.orientation.x, pose.orientation.y, pose.orientation.z, pose.orientation.w),
            )
        else:
            translation = transform.transform.translation
            rotation = transform.transform.rotation
            values = (
                transform.header.frame_id or "map",
                (translation.x, translation.y, translation.z),
                (rotation.x, rotation.y, rotation.z, rotation.w),
            )
        self._telemetry.extend(
            pose_observations(
                timestamp=timestamp,
                run_id=context.run_id,
                node_id=context.node_id,
                invocation_id=context.invocation_id,
                frame_id=values[0],
                position=values[1],
                orientation=values[2],
            )
        )

    def _record_action(
        self,
        context: ExecutionContext,
        action_id: str,
        phase: ActionPhase,
        message: str | None = None,
    ) -> None:
        self._telemetry.append(
            Observation.action_state(
                timestamp=datetime.now(UTC),
                run_id=context.run_id,
                node_id=context.node_id,
                invocation_id=context.invocation_id,
                action=ActionState(action_id, phase, message),
            )
        )

    def _navigation_terminal(self) -> None:
        self._active_navigation = None

    async def close(self) -> None:
        self._executor.shutdown()
        self._node.destroy_node()
        self._thread.join(timeout=2)
        if self._thread.is_alive():
            raise RuntimeError("TIAGo adapter executor thread did not terminate")
        if rclpy.ok():
            rclpy.shutdown()


class _RosActionInvocation(CapabilityInvocation):
    def __init__(
        self,
        handle: Any,
        *,
        context: ExecutionContext,
        action_id: str,
        output: dict[str, object],
        record_action: Any,
        on_terminal: Any | None = None,
    ) -> None:
        self._handle = handle
        self._context = context
        self._action_id = action_id
        self._output = output
        self._record_action = record_action
        self._on_terminal = on_terminal
        self._task: asyncio.Task[CapabilityResult] | None = None

    async def result(self) -> CapabilityResult:
        if self._task is None:
            self._task = asyncio.create_task(self._wait_result())
        return await asyncio.shield(self._task)

    async def _wait_result(self) -> CapabilityResult:
        try:
            response = await _await_ros(self._handle.get_result_async())
            if response.status == GoalStatus.STATUS_SUCCEEDED:
                self._record_action(self._context, self._action_id, ActionPhase.SUCCEEDED)
                return CapabilityResult(status=ResultStatus.SUCCESS, output=self._output)
            if response.status == GoalStatus.STATUS_CANCELED:
                self._record_action(self._context, self._action_id, ActionPhase.CANCELED)
                return CapabilityResult(status=ResultStatus.CANCELED)
            self._record_action(
                self._context,
                self._action_id,
                ActionPhase.FAILED,
                f"ROS goal status {response.status}",
            )
            return CapabilityResult(
                status=ResultStatus.FAILURE,
                error=ExecutionError(
                    code=ErrorCode.CAPABILITY_FAILED,
                    message="ROS action failed",
                    details={"ros_status": int(response.status)},
                ),
            )
        finally:
            if self._on_terminal is not None:
                self._on_terminal()

    async def request_cancel(self) -> CancellationDisposition:
        if self._task is not None and self._task.done():
            return CancellationDisposition.ALREADY_COMPLETE
        response = await _await_ros(self._handle.cancel_goal_async())
        if response.goals_canceling:
            return CancellationDisposition.ACCEPTED
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)


class _ImmediateInvocation(CapabilityInvocation):
    def __init__(self, value: CapabilityResult) -> None:
        self._value = value

    async def result(self) -> CapabilityResult:
        return self._value

    async def request_cancel(self) -> CancellationDisposition:
        return CancellationDisposition.ALREADY_COMPLETE

    async def detach(self) -> None:
        return None


def _failure(status: str, message: str) -> _ImmediateInvocation:
    return _ImmediateInvocation(
        CapabilityResult(
            status=ResultStatus.FAILURE,
            error=ExecutionError(
                code=ErrorCode.CAPABILITY_FAILED,
                message=message,
                details={"ros_status": status},
            ),
        )
    )


def _pose_stamped(node: Node, frame_id: str, target: NamedLocation) -> PoseStamped:
    pose = PoseStamped()
    pose.header.frame_id = frame_id
    pose.header.stamp = node.get_clock().now().to_msg()
    pose.pose.position.x = target.x
    pose.pose.position.y = target.y
    pose.pose.orientation.z = math.sin(target.yaw / 2)
    pose.pose.orientation.w = math.cos(target.yaw / 2)
    return pose


def _message_time(message: Any) -> datetime:
    stamp = message.header.stamp
    return ros_timestamp(int(stamp.sec), int(stamp.nanosec))


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _transform_point(
    transform_stamped: Any, point: tuple[float, float, float]
) -> tuple[float, float, float]:
    transform = transform_stamped.transform
    rotation = transform.rotation
    norm = math.sqrt(
        rotation.x * rotation.x
        + rotation.y * rotation.y
        + rotation.z * rotation.z
        + rotation.w * rotation.w
    )
    if norm == 0.0:
        raise ValueError("TF quaternion must be non-zero")

    x = rotation.x / norm
    y = rotation.y / norm
    z = rotation.z / norm
    w = rotation.w / norm
    px, py, pz = point
    translated = transform.translation
    return (
        translated.x
        + (1.0 - 2.0 * (y * y + z * z)) * px
        + 2.0 * (x * y - z * w) * py
        + 2.0 * (x * z + y * w) * pz,
        translated.y
        + 2.0 * (x * y + z * w) * px
        + (1.0 - 2.0 * (x * x + z * z)) * py
        + 2.0 * (y * z - x * w) * pz,
        translated.z
        + 2.0 * (x * z - y * w) * px
        + 2.0 * (y * z + x * w) * py
        + (1.0 - 2.0 * (x * x + y * y)) * pz,
    )


def _to_concurrent(future: Any) -> Future[Any]:
    result: Future[Any] = Future()

    def complete(done: Any) -> None:
        exception = done.exception()
        if exception is None:
            result.set_result(done.result())
        else:
            result.set_exception(exception)

    future.add_done_callback(complete)
    return result


async def _await_ros(future: Any) -> Any:
    return await asyncio.wrap_future(_to_concurrent(future))
