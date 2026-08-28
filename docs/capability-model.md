# Capability Model

A RoboArc capability is a stable, product-level robot behavior. It describes **what a robot can do** without exposing **how that behavior is implemented**.

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

Shared capabilities use stable semantic IDs when multiple robots can reasonably implement the same contract:

```text
navigation.goto
navigation.stop
head.look_at
speech.say
manipulation.open_gripper
manipulation.close_gripper
perception.detect_object
```

Robot-specific behaviors should remain explicit rather than being forced into a false common denominator:

```text
unitree.dance
reachy.antennas.wave
tiago.torso.raise
```

## Minimal manifest

A v0.1 manifest can remain intentionally small:

```yaml
id: navigation.goto
version: 1
title: Go to
category: Navigation

inputs:
  target:
    type: pose
    required: true

execution:
  timeout_ms: 120000
  cancellable: true

progress:
  mode: stage

resources:
  - base_motion
```

The manifest should drive as much generated behavior as practical:

- Blockly block metadata;
- inspector fields;
- input validation;
- capability discovery;
- documentation;
- compatibility checks.

Specialized editor widgets should be introduced only for domain types that genuinely need them, such as map locations, poses, colors, images, or joint configurations.

## Handler contract

The first runtime implementation can use a Python contract similar to:

```python
async def execute(args: dict, ctx: ExecutionContext) -> CapabilityResult:
    ...
```

`ExecutionContext` provides runtime services such as:

- cancellation state;
- structured logging;
- progress reporting;
- execution/node identifiers;
- workflow variables;
- deadlines/timeouts.

A robot's existing API does not need to be redesigned for RoboArc. The adapter wraps it:

```python
async def navigation_goto(args, ctx):
    await robot.goto(args["target"])
    return CapabilityResult.success()
```

## Execution traits

Only a terminal result is required in the minimal contract.

| Trait | v0.1 contract | Meaning |
| --- | --- | --- |
| result | required | success/failure/canceled/timeout |
| progress | optional | running feedback |
| cancel | optional | cooperative cancellation |
| pause | deferred | suspend execution |
| resume | deferred | resume suspended execution |

The UI must reflect unsupported traits rather than pretending they exist.

## Progress model

Progress should support increasing levels of fidelity.

### None

The adapter only knows that execution is running.

```text
Running...
```

### Stage

The adapter exposes meaningful phases:

```text
Planning -> Navigating -> Arriving
```

### Percent

The adapter exposes or derives quantitative progress:

```text
53%
```

Percent progress should include provenance:

```yaml
progress:
  mode: percent
  source: native   # or estimated
```

Estimated progress must be presented as approximate. For example, navigation may estimate completion from path or remaining distance, but that estimate should not be confused with a native controller metric.

A structured progress event may eventually contain:

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

A robot profile declares which capabilities are available through a specific adapter/configuration:

```yaml
id: tiago-sim
adapter: tiago

capabilities:
  - navigation.goto
  - navigation.stop
  - head.look_at
  - speech.say
  - manipulation.pick
  - manipulation.place
```

The editor should use the active profile to filter or annotate the available capability palette.

## Portability is semantic

Two robots exposing `navigation.goto` are not automatically equivalent. A robust contract eventually needs to address:

- coordinate frame and pose conventions;
- units and ranges;
- map/location identity;
- speed and acceleration constraints;
- preconditions and robot state;
- workspace and payload limits;
- asynchronous behavior and feedback;
- timeout and cancellation guarantees;
- result/error taxonomy.

v0.1 should not model all of these at once, but the manifest format should remain extensible enough to add them without redefining the capability identity.

## Resource declarations

Capabilities may declare logical resources:

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

This allows future static validation or runtime arbitration to detect incompatible parallel actions. v0.1 may only validate obvious conflicts; a full resource scheduler is deferred.
