# Minimal Reachy 2 MuJoCo lane

This image is a small, source-built development lane for RoboArc portability
work. It packages Pollen Robotics' open-source `reachy2_mujoco` fake SDK server
with MuJoCo and a virtual X display. It deliberately does not include ROS 2,
RViz, Gazebo, VNC, audio, cameras, or the full Reachy hardware/SDK server.

The source revisions and MuJoCo version are recorded in
[`versions.env`](versions.env). This is a functional source build, not a
reproduction of Pollen's larger `pollenrobotics/reachy2` image.

The pinned `reachy2_mujoco` revision refers to a missing `desk_scene.xml`.
The Dockerfile verifies that exact upstream line and changes it to the included
`table_scene.xml`; the build fails rather than silently applying the patch if
the upstream source no longer matches.

Build from the repository root:

```bash
docker build -f docker/reachy2-minimal/Dockerfile -t roboarc-reachy2-minimal .
```

Run the fake SDK server (RPyC on port `18861`):

```bash
docker run --rm -p 18861:18861 roboarc-reachy2-minimal
```

The default `runtime` target excludes recording tools. Build the explicit proof
target only when producing the required visual evidence:

```bash
docker build --target proof \
  -f docker/reachy2-minimal/Dockerfile \
  -t roboarc-reachy2-proof .
```

The proof target can capture the virtual display while the host runs the
canonical Workflow IR through the SDK adapter. Record the UTC origin before
starting ffmpeg, pass that exact value to `tests/reachy/run_manual.py`, then
stop ffmpeg with `SIGINT` so the MP4 trailer is finalized. The required output
set is `reachy-observable.json`, `result.json`, `reachy-observable.jsonl`,
`reachy-observable.rrd`, `review.json`, and `mujoco-review.mp4` from one run.

The server is reachable by Pollen's SDK-shaped client at `localhost:18861`.
The current upstream server starts a MuJoCo passive viewer, so the image uses
Xvfb even when no host display is attached. A RoboArc adapter should remain
outside `roboarc.contracts` and `roboarc.runtime` and treat this endpoint as a
native transport boundary.

This lane is the documented v0.3 visual proof lane for adapter development and
deterministic integration checks. The completed proof set lives in
`artifacts/reachy-proof-final` and can be checked as a whole with:

```bash
python scripts/validate_review_artifacts.py artifacts/reachy-proof-final
```

Add `--check-media` when `ffprobe` is available to inspect the recording, or
`--check-rerun` when the `rerun` CLI is available to verify the native recording.
