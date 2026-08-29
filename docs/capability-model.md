# Capability Model

A RoboArc capability is a stable, product-level robot behavior. It describes **what a robot can do** without exposing **how it is implemented**.

```text
Robot native interface
ROS 2 / SDK / REST / gRPC / ...
              |
              v
        Robot Adapter
              |
              v
      RoboArc Capability
```

## Standard and robot-specific capabilities

Shared capabilities should use stable semantic IDs only after multiple adapters demonstrate compatible contracts:

```text
navigation.goto_location
navigation.stop
head.look_at
speech.say
```

Robot-specific behavior remains explicit rather than being forced into a false common denominator:

```text
unitree.dance
reachy.antennas.wave
tiago.torso.raise
```

Early MockAdapter capabilities use the `demo.*` namespace so test fixtures do not accidentally define standards.

## Minimal manifest

The implemented manifest is intentionally small and versioned:

```yaml
manifest_schema_version: 1
id: navigation.goto_location
version: 1
title: Go to location
category: Navigation

inputs:
  target:
    type: map_location
    required: true

outputs: {}

execution:
  timeout_ms: 120000
  cancellable: true

progress:
  mode: stage
  source: null

resources:
  - base_motion
```

Supported primitive field types currently include string, integer, finite number, boolean, duration in milliseconds, and named map location. Fields may declare required/default/enum/minimum/maximum constraints where semantically valid.

The manifest should drive:

- Blockly block metadata;
- inspector fields;
- preflight input validation;
- runtime output validation;
- capability discovery;
- documentation;
- compatibility checks.

Specialized widgets should be introduced only with explicit domain serialization rules.

## Exact capability references

A workflow does not invoke a bare capability name:

```json
{
  "capability": {
    "id": "navigation.goto_location",
    "version": 1
  }
}
```

A robot profile similarly lists exact contract references. Adapter upgrades must not silently reinterpret an existing workflow as a new incompatible capability version.

## Adapter invocation contract

The runtime asks an adapter to start one invocation:

```python
async def invoke(capability, args, context) -> CapabilityInvocation:
    ...
```

The invocation exposes:

```python
async def result() -> CapabilityResult: ...
async def request_cancel() -> CancellationDisposition: ...
async def detach() -> None: ...
```

This lifecycle is more precise than treating every robot action as a cancellable Python coroutine. A local coroutine cancellation does not prove that the physical operation stopped.

`ExecutionContext` supplies runtime services such as:

- run, node, and invocation identifiers;
- structured logging;
- stage or percentage progress reporting;
- progress provenance.

Future contexts may add variables and deadlines once their semantics are part of Workflow IR.

## Execution traits

Only a terminal result is required. Richer behavior is progressive:

| Trait | Current contract | Meaning |
| --- | --- | --- |
| result | required | success/failure/canceled/timeout |
| progress | optional | none/stage/percent |
| cancellation | optional | native cancellation request and terminal acknowledgement |
| pause/resume | deferred | suspend and resume native work |

The UI must expose unsupported cancellation instead of pretending it exists.

## Progress

Progress modes are:

```text
none
stage
percent
```

Percentage progress must state whether it is native or estimated. Estimated progress must be presented as approximate.

A structured progress event may contain:

```json
{
  "stage": "navigating",
  "percent": 53.0,
  "source": "estimated",
  "message": "Navigating to reception",
  "current": 5.3,
  "total": 10.0,
  "unit": "m"
}
```

## Robot profiles

A profile declares the capabilities available through one adapter/configuration:

```yaml
profile_schema_version: 1
id: tiago-sim
title: TIAGo Simulation
adapter: tiago
capabilities:
  - id: navigation.goto_location
    version: 1
  - id: navigation.stop
    version: 1
  - id: head.look_at
    version: 1
  - id: speech.say
    version: 1
```

The editor uses the active profile to generate or annotate its capability palette.

## Portability is semantic

Matching IDs and versions are necessary but not sufficient. A robust shared contract eventually needs to define:

- coordinate frames and pose conventions;
- units and valid ranges;
- map/location identity;
- speed and acceleration constraints;
- preconditions and robot state;
- workspace and payload limits;
- feedback fidelity;
- timeout and cancellation guarantees;
- result/error taxonomy.

Standardize capabilities only after real adapters validate these assumptions.

## Resource declarations

Capabilities may declare logical resources such as:

```yaml
resources:
  - base_motion
```

or:

```yaml
resources:
  - left_arm
  - left_gripper
```

No parallel node is implemented yet. These declarations preserve a path toward future static conflict checks and resource arbitration without requiring a scheduler in the current core.
