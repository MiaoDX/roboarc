# Runtime

The RoboArc runtime executes validated Workflow IR and translates capability invocations into calls on the active robot adapter.

The v0.1 runtime should optimize for clarity and observability rather than durability or distributed execution.

## Execution state

At the workflow and node level, the initial state model can remain small:

```text
PENDING -> RUNNING -> SUCCEEDED
                  \-> FAILED
                  \-> CANCELED
                  \-> TIMED_OUT
```

A terminal capability result should be normalized to one of:

- success;
- failure;
- canceled;
- timeout.

Robot/vendor-specific details belong in structured result metadata or error fields.

## Execution events

The runtime should emit structured events with stable workflow/node IDs. A minimal event envelope might look like:

```json
{
  "run_id": "run-123",
  "node_id": "go-reception",
  "type": "progress",
  "timestamp": "...",
  "data": {
    "stage": "navigating",
    "percent": 42,
    "source": "native"
  }
}
```

Useful v0.1 event types include:

- run started / finished;
- node started / finished;
- progress;
- log;
- error;
- cancellation requested / completed.

The Web UI consumes these events over WebSocket to highlight the current Blockly block and display live status.

## Cancellation

Cancellation is cooperative and capability-dependent.

A cancellation request should:

1. mark the execution context as canceled;
2. propagate into the currently running control-flow branch(es);
3. call the adapter's native cancellation hook when the capability declares `cancellable: true`;
4. wait for bounded cleanup before producing a terminal result.

If a native API cannot cancel an operation, RoboArc should expose that limitation. It must not report an operation as canceled while the robot is still executing it.

Pause/resume is deliberately deferred because its semantics are much less portable than cancellation.

## Parallel execution

`parallel` introduces real robot concerns immediately. v0.1 should support a conservative form and reject obvious conflicts when branches require the same declared resource.

The first implementation does not need a sophisticated scheduler. A future resource manager may support leases, priorities, preemption, and deadlock prevention.

## Timeout

A runtime-level deadline is useful even when a robot API has no native timeout. However, a timeout does not imply the physical action stopped. When possible, timeout handling should request native cancellation and report cleanup failure explicitly.

Dedicated per-node timeout syntax can be deferred from the IR while the runtime still enforces capability default timeouts from manifests.

## Retry and idempotency

Automatic retry is intentionally deferred. Robot actions are frequently non-idempotent: retrying `pick`, `open_door`, or `move_relative` can change the physical world in undesirable ways.

When retry is introduced, capabilities should be able to declare or document retry safety rather than assuming it globally.

## Durability and restart semantics

v0.1 execution is in-memory. If the runtime process exits, the run is considered interrupted and is not automatically resumed.

This is a deliberate non-goal for the first release. Durable workflows require explicit semantics for:

- persisted state;
- reconciliation with actual robot state after restart;
- idempotency;
- in-flight native actions;
- compensation/recovery;
- versioned workflow provenance.

These should not be approximated with a simple database checkpoint.

## Implementation direction

The initial runtime is expected to use:

- Python;
- `asyncio` for structured asynchronous execution;
- Pydantic for contracts and validation;
- FastAPI for HTTP/WebSocket endpoints.

Python minimizes integration friction with robotics and ML ecosystems. A Rust runtime using Tokio/Axum/Serde remains a possible later option if deployment requirements demand a smaller, more strongly isolated edge daemon.

Node.js is best kept on the Web/tooling side unless a concrete robot integration makes it compelling.

## Trust model

v0.1 assumes capability handlers are trusted code installed by the operator. Workflow documents are declarative and cannot contain arbitrary executable Python, JavaScript, or shell commands.

This boundary is important even before authentication is added: it keeps validation meaningful and prevents the visual editor from becoming a generic remote-code-execution surface.

## Observability

Every run should have a `run_id`, and every executable node should have a stable `node_id`. Logs and events should carry both.

This minimal discipline enables future:

- timeline views;
- replay;
- execution comparisons;
- provenance;
- telemetry export;
- debugging across Web/runtime/adapter boundaries.
