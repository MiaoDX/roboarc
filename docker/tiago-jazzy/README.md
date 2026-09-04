# TIAGo Jazzy manual proof lane

This lane keeps ROS, Nav2, Gazebo, and TIAGo dependencies outside the RoboArc
core package. It runs the unchanged Workflow IR through `Runtime` and
`TiagoRosAdapter`, then writes Runtime events plus ROS pose, trajectory, action,
and feedback observations to one JSONL trace.

The repository's pinned overlay and four-capability workflow have completed
this proof successfully; the commands below are the reproducible manual lane,
not an always-on CI dependency or production-support promise.

The public PAL Robotics `tiago_simulation` repository currently documents a
ROS 2 Humble workspace and does not publish a Jazzy branch. This image builds a
pinned public PAL workspace and applies the narrowly scoped Jazzy/Harmonic
patches in `patches/`. Upstream repositories are fixed to immutable commits in
`tiago.repos`; the patch step fails if an expected source hunk changes.

Build the lane:

```bash
docker build -f docker/tiago-jazzy/Dockerfile -t roboarc-tiago-jazzy .
```

Run the no-Gazebo contract checks in the container:

```bash
docker run --rm roboarc-tiago-jazzy \
  python -m pytest -p pytest_asyncio.plugin tests/tiago/test_profile.py \
  tests/tiago/test_telemetry_bridge.py
```

Run the single-container headless Gazebo proof with a durable artifact
directory:

```bash
mkdir -p artifacts
docker run --rm --network host \
  -v "$PWD/artifacts:/artifacts" \
  roboarc-tiago-jazzy docker/tiago-jazzy/run-proof.sh
```

The image exposes `tiago_gazebo`, Nav2's `/navigate_to_pose`,
`map -> base_footprint` TF, the stamped mobile-base command topic, and the head
trajectory controller. Speech is
deliberately a transport seam: the adapter publishes `std_msgs/String` on
`/roboarc/speech`, which a deployment may bridge to its installed TIAGo TTS
stack.

Successful proof outputs are `artifacts/tiago-observable.jsonl` and a native
Rerun `artifacts/tiago-observable.rrd`. They must include
the four workflow nodes and correlated `robot.pose`, `robot.trajectory`,
`action.state`, and `capability.progress` observations. Gazebo GUI and RViz may
be launched separately for diagnosis; neither is a RoboArc UI dependency.

For an optional GUI review recording, the host needs Docker, Xvfb, and
GStreamer with `ximagesrc`, `x264enc`, `h264parse`, and `mp4mux`:

```bash
./docker/tiago-jazzy/run-gazebo-review.sh \
  --image roboarc-tiago-jazzy:repro \
  --output artifacts/tiago-proof-final/gazebo-review.mp4
```

The review wrapper uses NVIDIA GPU rendering by default (`--gpus all`) and
validates the resulting MP4 inside the same image with `ffprobe`. Use
`--software` only on a host without a usable NVIDIA runtime.

The wrapper uses the same launch lifecycle and workflow, records a fixed
1600x900 display after the TIAGo controllers and Nav2 report ready, with roughly
three seconds of pre-roll and post-roll. It writes JSONL/Rerun artifacts beside
the video. Validate it with:

The wrapper prints the validated codec, dimensions, and duration. The image
contains `ffprobe`, so validation does not depend on host media packages.

To run the HTTP/WebSocket API with the real TIAGo adapter inside the ROS-enabled
image, use:

```bash
roboarc serve --tiago --host 0.0.0.0 --port 8000
```

The default `roboarc serve` remains the MockAdapter Workbench API. The explicit
TIAGo mode loads the separate `roboarc_tiago` integration package; ROS imports
do not enter `roboarc.contracts` or `roboarc.runtime`.

Serve all valid review artifacts on the LAN with:

```bash
./scripts/serve_review.sh --host 0.0.0.0 --artifacts artifacts
```

Review URL: `http://<host-lan-ip>:5173/?review`.
