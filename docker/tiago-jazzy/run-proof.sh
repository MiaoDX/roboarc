#!/usr/bin/env bash
set -euo pipefail

if ! ros2 pkg prefix tiago_gazebo >/dev/null 2>&1; then
  echo "tiago_gazebo is unavailable." >&2
  echo "Mount a ROS 2 Jazzy TIAGo overlay at /tiago_ws before running this proof." >&2
  exit 2
fi

cleanup() {
  if [[ -n "${gazebo_pid:-}" ]]; then
    kill "$gazebo_pid" 2>/dev/null || true
    wait "$gazebo_pid" 2>/dev/null || true
  fi
}
trap cleanup EXIT

ros2 launch tiago_gazebo tiago_gazebo.launch.py \
  is_public_sim:=True \
  navigation:=True \
  arm_type:=no-arm \
  end_effector:=no-end-effector \
  ft_sensor:=no-ft-sensor \
  camera_model:=no-camera \
  moveit:=False \
  tuck_arm:=False \
  rviz:=False \
  gzclient:=False \
  gazebo_version:=gazebo &
gazebo_pid=$!

stack_ready() {
  ros2 lifecycle get /amcl 2>/dev/null | grep -q 'active' \
    && ros2 lifecycle get /bt_navigator 2>/dev/null | grep -q 'active' \
    && ros2 control list_controllers 2>/dev/null \
      | grep -q '^mobile_base_controller.*active' \
    && ros2 control list_controllers 2>/dev/null \
      | grep -q '^head_controller.*active'
}

for _ in $(seq 1 180); do
  if stack_ready; then
    break
  fi
  sleep 1
done

if ! stack_ready; then
  echo "TIAGo controllers and Nav2 did not become active within 180 seconds." >&2
  exit 3
fi

if ! ros2 action list | grep -qx '/navigate_to_pose'; then
  echo "Nav2 is active but /navigate_to_pose is unavailable." >&2
  exit 4
fi

if ! ros2 action list | grep -qx '/head_controller/follow_joint_trajectory'; then
  echo "TIAGo head controller is active but its trajectory action is unavailable." >&2
  exit 5
fi

python -m tests.tiago.run_manual \
  --workflow examples/workflows/tiago-observable.json \
  --trace /artifacts/tiago-observable.jsonl \
  --rerun /artifacts/tiago-observable.rrd
