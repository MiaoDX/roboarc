# Gazebo Visual Review

## Plan Ledger

- Status: COMPLETE - GPU product run and artifact validation passed
- Roadmap owner: `docs/development-plan.md` v0.2b / TIAGo proof follow-up
- Source: recovered from Codex session `01a056cd-0805-7b01-8fca-52551e8ed3e0`
- Scope decision: add a reproducible Gazebo GUI review artifact while keeping
  the existing headless proof authoritative.
- Follow-up approval: add a manifest-backed, read-only Workflow/Blockly review
  route for recorded artifacts; live Gazebo streaming remains out of scope.
- Follow-up implementation: add reusable Execution Timeline metadata and
  trace-derived Blockly highlighting during recorded media playback; the
  timeline remains media-agnostic and live synchronization remains out of scope.

## Goal

Give reviewers a playable recording of the real four-node TIAGo Jazzy/Gazebo
workflow, viewable from another machine on the LAN, without adding live Gazebo
streaming, VNC, or simulator dependencies to RoboArc core.

## Scope

- Keep `docker/tiago-jazzy/run-proof.sh` as the authoritative headless proof.
- Add one independent, optional Gazebo GUI review wrapper.
- Reuse the `roboarc-tiago-jazzy:repro` image, the existing
  `tiago-observable.json` workflow, and the existing launch/readiness lifecycle.
- Start Gazebo GUI with `gzclient:=True` inside a fixed host `Xvfb` display.
- Record a fixed-size H.264 MP4 through host GStreamer, targeting `1600x900`.
- Include about three seconds of pre-roll, the workflow, and about three
  seconds of post-roll.
- Produce `artifacts/tiago-proof-final/gazebo-review.mp4` plus the same-run
  JSONL/Rerun artifacts.
- Document serving the artifact over the LAN with `python -m http.server`.

## Non-Goals

- Do not change Workflow IR, Runtime, or capability contracts.
- Do not add Gazebo GUI, VNC, WebRTC, or X11 dependencies to the core package.
- Do not make another machine run the Gazebo client.
- Do not change the default behavior of the headless proof.
- Do not embed a live Gazebo, VNC, or WebRTC viewer in the Workbench.
- Do not implement noVNC, RViz streaming, robot camera streaming, or generic
  ROS/Gazebo LAN transport.
- Do not add a second simulator or launch recipe.

## Entity Budget

- Reuse the existing TIAGo image, proof lifecycle, workflow, JSONL/Rerun
  artifact contract, host Xvfb, and host GStreamer.
- Add only a thin review wrapper, video artifact path, and documentation.
- Parameterize `run-proof.sh` minimally only if lifecycle reuse otherwise cannot
  be achieved.
- Interactive camera control, noVNC, authentication, real-time streaming, and
  cross-host ROS transport require a new approval.

## Required Context

- `docker/tiago-jazzy/run-proof.sh`
- `docker/tiago-jazzy/Dockerfile`
- `docker/tiago-jazzy/README.md`
- `examples/workflows/tiago-observable.json`
- `tests/tiago/run_manual.py`
- `src/roboarc/rerun.py`
- `STATUS.md`

## Acceptance Criteria

- The existing headless proof still succeeds unchanged.
- The review command uses the same workflow and ROS/Gazebo launch semantics.
- Gazebo GUI starts in a fixed virtual display and produces a non-empty,
  playable video.
- The framing stably shows TIAGo and the relevant scene area.
- Reviewers can observe the base moving from its start to reception and the
  head controller turning.
- The video includes pre-run still, execution, and terminal still frames.
- The same run reports `succeeded`, with all four capability nodes and root
  successful.
- JSONL/Rerun retain identity, timestamp, progress, pose, and trajectory
  correlation.
- `ffprobe` validates codec, resolution, duration, and readable frames.
- Documentation gives an explicit LAN artifact-serving command and URL.
- Core Python/Web checks and the ROS import boundary remain unaffected.

## Verification

Deterministic checks:

```bash
git diff --check
ruff check .
mypy src/roboarc
python -m compileall -q src scripts
python -m pytest
python scripts/generate_schemas.py
git diff --exit-code -- schemas
```

Integration checks:

- TIAGo profile/telemetry tests.
- Existing `docker/tiago-jazzy/run-proof.sh`.
- JSONL identity/timestamp correlation audit.
- `rerun rrd verify <recording>`.

Product run:

```bash
./docker/tiago-jazzy/run-gazebo-review.sh \
  --image roboarc-tiago-jazzy:repro \
  --output artifacts/tiago-proof-final/gazebo-review.mp4
```

The command must execute the real four-node workflow, not a mock or shortened
visual demo.

Local/live manual gates require host Docker, Xvfb, GStreamer (`ximagesrc`,
`x264enc`, `h264parse`, `mp4mux`), software-rendering fallback where needed,
manual inspection of opening/navigation/head-turn/terminal frames, `ffprobe`,
and local browser playback. Serve the result with:

```bash
python -m http.server 8080 \
  --directory artifacts/tiago-proof-final \
  --bind 0.0.0.0
```

Review URL: `http://<host-lan-ip>:8080/gazebo-review.mp4`.

## Completion Evidence

- GPU product command completed with `roboarc-tiago-jazzy:repro` and
  `--gpus all`; the container detected the host RTX 3090.
- The final real four-node workflow returned `state: succeeded` and wrote 1,339
  observations beside the recording.
- Container `ffprobe` validated `h264`, `1600x900`, and `14.793667` seconds;
  frame sampling and correlated poses proved approximately 0.766 m of base
  motion, and action telemetry proved navigation/head success.
- `rerun rrd verify artifacts/tiago-proof-final/tiago-observable.rrd` passed,
  as did Ruff, mypy, compileall, pytest (44 passed, 2 ROS skips), 27 Web unit
  tests, 8 Chromium workflows, and diff checks.
- The read-only review route loaded the same run's validated manifest, rendered
  canonical Workflow IR as Blockly, and served its MP4/JSONL/RRD through the
  LAN-visible same-origin artifact proxy.
- Review playback now uses the manifest's UTC media origin and the same-run
  JSONL node events to highlight the active Blockly node on timeupdate and seek.

## Execution And Stop Gates

- The main session owns wrapper design, live proof, visual acceptance, docs,
  and final audit. No worker is required initially.
- Stop with `BLOCKED_NEEDS_LOCAL_VALIDATION` if Docker/X11/GPU is unavailable,
  GUI startup is unstable, framing is nondeterministic, or the video cannot
  visibly prove base movement and head rotation.
- Do not respond to those failures by adding noVNC, WebRTC, or another simulator
  route in this slice.
- Mark complete only after headless proof, GUI product run, video inspection,
  artifact validation, and docs all pass.

## Approval

This contract was approved with `LGTM` in the source session. The next context
should execute it without reopening the route unless a listed stop gate fires.
