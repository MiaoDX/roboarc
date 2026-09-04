#!/usr/bin/env bash
set -euo pipefail

workspace=${1:-/tiago_ws}
patch_root=${2:-/overlay-patches}

apply_repo_patch() {
  local repo=$1
  local patch=$2

  git -C "$workspace/src/$repo" apply --check "$patch_root/$patch"
  git -C "$workspace/src/$repo" apply "$patch_root/$patch"
}

apply_repo_patch pal_gazebo_worlds pal_gazebo_worlds.patch
apply_repo_patch pmb2_navigation pmb2_navigation.patch
apply_repo_patch pmb2_robot pmb2_robot.patch
apply_repo_patch tiago_robot tiago_robot.patch

# PAL's plugin package is Gazebo Classic-only. Harmonic equivalents come from
# ros_gz and gz_ros2_control, while keeping this checkout pins the source graph.
touch "$workspace/src/pal_gazebo_plugins/COLCON_IGNORE"
