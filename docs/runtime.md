# Runtime

The RoboArc runtime executes validated Workflow IR and translates capability nodes into operations on the active robot adapter. The v0.1 runtime optimizes for explicit semantics and observability rather than durability or distributed execution.

## Execution states

Workflow and node execution use a small state model:

```text
PENDING -> RUNNING -> SUCCEEDED
                  \-> FAILED
                  \-> CANCELED
                  \-> TIMED_OUT

RUNNING -> CANCELING -> CANCELED
                     \-> FAILED
                     \-> SUCCEEDED
```

`CANCELING` is non-terminal. A cancellation request does not imply that the robot stopped. If an operation completes successfully before cancellation takes effect, the runtime reports the observed successful result. If the native operation cannot be confirmed terminal within the cleanup deadline, the runtime reports `FAILED` with `cancellation_incomplete` rather than claiming `CANCELED`.

A run or node enters exactly one terminal state.

## Adapter invocation lifecycle

The runtime does not model a robot action as a bare coroutine. An adapter starts a `CapabilityInvocation` that exposes three lifecycle operations:

```python
async def result() -> CapabilityResult: ...
async def request_cancel() -> CancellationDisposition: ...
async def detach() -> None: ...
```

`request_cancel()` returns whether cancellation was accepted, unsupported, or the operation was already complete. Acceptance is not completion; the runtime still waits for the invocation's terminal result.

`detach()` releases local observation after bounded cleanup expires. It must not be interpreted as stopping the native action.

## Result normalization

A terminal adapter result is normalized to:

```text
success
failure
canceled
timeout
```

Successful output is checked against the capability manifest. Missing required output, unknown output, or invalid output type becomes an `adapter_contract_violation` failure.

Vendor-specific details remain in structured error/result metadata.

## Events

Every event contains stable run/node identity and replay metadata:

```json
{
  "event_protocol_version": 1,
  "event_id": "...",
  "seq": 8,
  "run_id": "run-...",
  "node_id": "go-reception",
  "type": "capability.progress",
  "occurred_at": "...",
  "data": {
    "stage": "navigating"
  }
}
```

`seq` is monotonically increasing within one run. Clients reconnect with `after_seq=N`, replay events after `N`, and then continue consuming live events.

Current event types include:

- run started, cancellation requested, and finished;
- node started, cancellation requested, and finished;
- capability progress;
- structured log;
- structured error.

## Sequence semantics

`sequence` executes children in declaration order and fails fast. The first child that fails, times out, or is canceled determines the sequence result. No later child starts.

If a run cancellation request is present between children, the sequence terminates as canceled.

## Wait semantics

`wait` is runtime-native and immediately cancellable. It has no robot resources and returns no output.

## Timeout semantics

A capability manifest supplies a default deadline. When the deadline expires, the runtime requests native cancellation and waits for bounded cleanup.

- If a terminal result is observed during cleanup, the node is reported as `TIMED_OUT`, with the observed terminal status retained in error metadata.
- If no terminal result is observed, the node fails with `cancellation_incomplete` because the physical operation may still be running.

An explicit Workflow IR timeout node is deferred.

## Cancellation semantics

A run cancellation request:

1. records `run.cancel_requested`;
2. prevents new sequence children from starting;
3. records `node.cancel_requested` for the active capability;
4. asks the invocation to cancel;
5. waits for a terminal native result up to the configured cleanup deadline;
6. reports the observed terminal state truthfully.

Pause/resume is deferred because its semantics are substantially less portable.

## Parallel execution

Parallel execution is not part of the implemented v0.1 IR. Resource declarations remain in capability manifests so a future `parallel_all` design can statically reject obvious conflicts. Join behavior, sibling cancellation, cleanup, and result aggregation must be specified before implementation.

## HTTP and WebSocket transport

The local FastAPI service provides:

```text
GET  /api/v1/health
GET  /api/v1/profile
GET  /api/v1/capabilities
POST /api/v1/workflows/validate
POST /api/v1/workflows/compatibility
POST /api/v1/runs
GET  /api/v1/runs/{run_id}
POST /api/v1/runs/{run_id}/cancel
GET  /api/v1/runs/{run_id}/events?after_seq=N
WS   /api/v1/runs/{run_id}/events?after_seq=N
```

HTTP handles discovery, validation, control, snapshots, and replay. WebSocket provides live events after replaying missed history.

## Profiles and compatibility preflight

`roboarc serve --profile PROFILE_ID` selects one adapter at process startup.
The supported core profiles are `mock` and `deterministic-simulation`; the
isolated adapters provide `tiago-sim` and `reachy2-sim`. `GET /api/v1/profile`
reports the stable active profile. `reachy2-sim` connects to the optional
Pollen MuJoCo SDK endpoint selected by `REACHY_HOST` (default `127.0.0.1`).

Workflow v1 may optionally carry `profile_id`, and manifest v1 may optionally
carry `compatible_profiles`. Compatibility reports are keyed by capability
node ID and retain the node's exact `{id, version}` reference. Each entry has
one status and machine-readable reason:

- `compatible`: `exact_capability_match` or `declared_profile_compatibility`;
- `missing`: `capability_missing`;
- `incompatible`: `capability_version_mismatch`;
- `unknown`: `profile_compatibility_unknown`.

All non-compatible statuses fail validation before the adapter is invoked.
Legacy workflows without `profile_id` retain exact-reference behavior. Every
started run pins the active `profile_id` in its start response, snapshot,
terminal result, and `run.started` event metadata.

### Reachy 2 capability matrix

| Capability | Inputs and units | Output | Progress | Cancellation | Native mapping | Visual assumption |
| --- | --- | --- | --- | --- | --- | --- |
| `reachy.arm.pose_joints@1` | `side` (`left`/`right`), seven named joint angles in degrees, `duration_ms` | selected `side`, `completed` | client-side estimated percent from deterministic interpolation steps | unsupported | `l_arm`/`r_arm.get_present_positions()`, `set_goal_positions()`, then `send_goal_positions()` | changing arm joint targets is visible in the pinned MuJoCo table scene |

The adapter treats each arm as the logical `arm_motion` resource. It does not
claim native completion feedback: success means every interpolation target was
accepted by the SDK-facing object without an exception. The upstream operation
has no reliable stop acknowledgement, so the capability is deliberately
non-cancellable. The always-on fake exposes the same SDK method shape; the
pinned MuJoCo lane remains the product-level visual proof.

## Durability

Runs and events are in memory. If the runtime process exits, active work is interrupted and is not resumed automatically.

Persisting a program counter is insufficient for physical workflow recovery. Safe restart requires reconciliation with robot/world state, native in-flight actions, idempotency, compensation, and workflow provenance. These semantics are deliberately deferred.

## Trust model

Capability handlers are trusted code installed by the operator. Workflow documents are declarative and cannot contain arbitrary executable Python, JavaScript, shell commands, or dynamically evaluated expressions.

## Observable traces

Runs can be exported as JSONL observation traces with `roboarc run WORKFLOW --trace trace.jsonl`.
Each record preserves the runtime event timestamp, run/node/invocation identity, event kind,
and payload. JSONL is the dependency-free interchange and diagnostic format.

For a native Rerun recording, install the optional integration and export an `.rrd` file:

```bash
python -m pip install -e ".[rerun]"
roboarc run examples/workflows/mock-demo.json --rerun run.rrd
roboarc view run.rrd
```

The complete dependency-free state-source path uses the deterministic simulation adapter:

```bash
roboarc simulate examples/workflows/simulation-observable.json \
  --trace simulation.jsonl --rerun simulation.rrd
```

Use `roboarc view run.rrd --web` to open the Web Viewer instead. The recording uses an ordered
`event_seq` timeline and the original event timestamp on a `wall_clock` timeline. All records are
available as structured JSON text; capability percentages are also logged as scalar series, and
robot pose/trajectory observations are logged spatially when present. Neither the Rerun SDK nor
viewer is imported by the runtime core or required for JSONL traces.
