#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash

if [[ -f /tiago_ws/install/setup.bash ]]; then
  source /tiago_ws/install/setup.bash
fi

set -u

exec "$@"
