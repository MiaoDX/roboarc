#!/usr/bin/env bash
set -euo pipefail

image="roboarc-tiago-jazzy:repro"
output="artifacts/tiago-proof-final/gazebo-review.mp4"
render_mode="gpu"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --image) image="$2"; shift 2;;
    --output) output="$2"; shift 2;;
    --software) render_mode="software"; shift;;
    *) echo "usage: $0 [--image IMAGE] [--output PATH] [--software]" >&2; exit 2;;
  esac
done
command -v Xvfb >/dev/null || { echo "Xvfb is required" >&2; exit 2; }
command -v gst-launch-1.0 >/dev/null || { echo "GStreamer is required" >&2; exit 2; }
command -v xdotool >/dev/null || { echo "xdotool is required" >&2; exit 2; }
mkdir -p "$(dirname "$output")"
artifact_dir="$(cd "$(dirname "$output")" && pwd)"
output="${artifact_dir}/$(basename "$output")"
start_gate="${artifact_dir}/.gazebo-review-start"
ready_gate="${artifact_dir}/.gazebo-review-ready"
end_gate="${artifact_dir}/.gazebo-review-end"
rm -f "$start_gate" "$ready_gate"
display="${DISPLAY:-:99}"
if [[ "$display" == :99 ]] && pgrep -f 'Xvfb :99' >/dev/null 2>&1; then
  display=:100
fi
Xvfb "$display" -screen 0 1600x900x24 -ac >/tmp/roboarc-xvfb.log 2>&1 & xvfb_pid=$!
sleep 1
kill -0 "$xvfb_pid" 2>/dev/null || { echo "Xvfb failed to start on $display" >&2; exit 3; }
docker_args=(--rm --network host)
if [[ "$render_mode" == gpu ]]; then
  docker_args+=(--gpus all)
  render_env=(-e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all -e LIBGL_ALWAYS_SOFTWARE=0)
else
  render_env=(-e LIBGL_ALWAYS_SOFTWARE=1)
fi
docker run "${docker_args[@]}" "${render_env[@]}" -e DISPLAY="$display" \
  -e QT_X11_NO_MITSHM=1 \
  -e XDG_RUNTIME_DIR=/tmp/xdg-runtime \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "${artifact_dir}:/artifacts" "$image" \
  env ROBOARC_GZCLIENT=True ROBOARC_TRACE=/artifacts/tiago-observable.jsonl \
  ROBOARC_RERUN=/artifacts/tiago-observable.rrd \
  ROBOARC_MANIFEST=/artifacts/review.json \
  ROBOARC_VIDEO="$(basename "$output")" \
  ROBOARC_READY_GATE=/artifacts/.gazebo-review-ready \
  ROBOARC_START_GATE=/artifacts/.gazebo-review-start \
  ROBOARC_END_GATE=/artifacts/.gazebo-review-end \
  docker/tiago-jazzy/run-proof.sh &
docker_pid=$!
cleanup() {
  rm -f "$start_gate" "$ready_gate"
  kill "${gst_pid:-}" "$docker_pid" "$xvfb_pid" 2>/dev/null || true
  wait "${gst_pid:-}" "$docker_pid" "$xvfb_pid" 2>/dev/null || true
}
trap cleanup EXIT

window_id=""
for _ in $(seq 1 180); do
  window_id="$(DISPLAY="$display" xdotool search --name 'Gazebo Sim' 2>/dev/null | head -1 || true)"
  [[ -n "$window_id" ]] && break
  sleep 1
done
[[ -n "$window_id" ]] || { echo "Gazebo GUI did not appear within 180 seconds" >&2; exit 3; }
DISPLAY="$display" xdotool windowmove "$window_id" 0 0 windowsize "$window_id" 1600 900
for _ in $(seq 1 180); do
  [[ -e "$ready_gate" ]] && break
  sleep 1
done
[[ -e "$ready_gate" ]] || { echo "TIAGo stack did not become ready for capture" >&2; exit 3; }
sleep 2

gst-launch-1.0 -e ximagesrc display-name="$display" use-damage=false \
  ! video/x-raw,framerate=30/1,width=1600,height=900 \
  ! videoconvert ! video/x-raw,format=I420 \
  ! x264enc tune=zerolatency speed-preset=ultrafast \
  ! h264parse ! mp4mux ! filesink location="$output" >/tmp/roboarc-gst.log 2>&1 & gst_pid=$!
date -u +%Y-%m-%dT%H:%M:%S.%NZ >"$start_gate"
sleep 3
wait "$docker_pid"
kill -INT "$gst_pid" 2>/dev/null || true
wait "$gst_pid" 2>/dev/null || true
[[ -s "$output" ]] || { echo "video capture is empty" >&2; exit 5; }
probe="$(docker run --rm --entrypoint ffprobe \
  -v "${artifact_dir}:/artifacts:ro" "$image" \
  -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height \
  -show_entries format=duration -of default=nw=1:nk=1 \
  "/artifacts/$(basename "$output")")"
printf '%s\n' "$probe"
grep -qx 'h264' <<<"$probe" || { echo "video codec is not H.264" >&2; exit 6; }
grep -qx '1600' <<<"$probe" || { echo "video width is not 1600" >&2; exit 6; }
grep -qx '900' <<<"$probe" || { echo "video height is not 900" >&2; exit 6; }
echo "wrote $output"
