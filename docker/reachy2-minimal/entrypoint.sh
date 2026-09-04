#!/usr/bin/env sh
set -eu

Xvfb "${DISPLAY}" -screen 0 1280x720x24 -ac +extension GLX +render -noreset >/tmp/reachy2-xvfb.log 2>&1 &
xvfb_pid=$!
trap 'kill "${xvfb_pid}" 2>/dev/null || true' EXIT INT TERM

if [ "$#" -eq 0 ]; then
    set -- reachy2-mujoco
fi

exec "$@"
