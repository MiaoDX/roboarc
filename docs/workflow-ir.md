# Workflow IR

Workflow IR is RoboArc's canonical representation of a robot program:

```text
Blockly workspace --compile--> Workflow IR --validate/execute--> Runtime
```

Blockly serialization preserves editing state, but it is not the executable contract. This separation permits additional authoring surfaces without changing runtime semantics.

## Implemented v0.1a node set

The current IR contains only:

- `sequence`;
- `wait`;
- `capability`.

This is intentional. `if`, references, loops, parallelism, retry, timeout, fallback, subflow, event, and guard nodes are deferred until their types, scope, result propagation, side effects, and cancellation behavior are specified.

## Example

```json
{
  "workflow_schema_version": 1,
  "id": "welcome-visitor",
  "name": "Welcome visitor",
  "workflow": {
    "id": "root",
    "type": "sequence",
    "children": [
      {
        "id": "settle",
        "type": "wait",
        "duration_ms": 250
      },
      {
        "id": "say-hello",
        "type": "capability",
        "capability": {
          "id": "speech.say",
          "version": 1
        },
        "args": {
          "text": "Hello!"
        }
      }
    ]
  }
}
```

Capability references include an exact contract version so adapter upgrades cannot silently change workflow meaning.

## Stable node IDs

Every node has a stable ID. Runtime events, visual highlighting, logs, and future timeline/replay features use that ID.

The schema rejects duplicate IDs, excessive depth, and excessive node count. An editor should preserve IDs for logically unchanged blocks and assign new IDs only to new logical nodes.

## Project documents

Saved authoring projects keep format evolution separate:

```json
{
  "project_format_version": 1,
  "name": "Welcome visitor",
  "editor": {
    "editor_state_version": 1,
    "type": "blockly",
    "state": {}
  },
  "workflow": {}
}
```

The editor state may evolve independently from Workflow IR. Execution always uses a validated current Workflow document, never raw Blockly state.

## Values

Current capability arguments are strict JSON literals validated against the selected manifest. The initial value vocabulary includes:

- string;
- integer;
- finite number;
- boolean;
- duration in milliseconds;
- named map location.

Domain values such as poses, object poses, joint configurations, images, and frames require explicit serialization and semantic contracts before introduction.

## Validation

Validation occurs before execution and reports issues against stable node IDs. Current checks include:

- known node shape through the discriminated schema;
- unique and bounded node structure;
- exact supported capability ID/version;
- required inputs;
- unknown inputs;
- primitive type and range constraints;
- strict JSON-compatible data.

The runtime separately validates successful adapter output against the declared output contract.

Validation is not a substitute for safety checks in robot controllers.

## Schema evolution

RoboArc separates these version domains:

```text
project_format_version
workflow_schema_version
editor_state_version
manifest_schema_version
profile_schema_version
event_protocol_version
capability contract version
```

Readers reject unsupported future schema versions. When a schema changes, migrations must be deterministic, testable, and produce the current canonical form before execution.

## Future conditions and references

A future conditional model should use a limited typed declarative structure rather than arbitrary expression evaluation, for example:

```json
{
  "op": "eq",
  "left": {"ref": "detect-person.result.found"},
  "right": true
}
```

Before implementing this, RoboArc must define output naming, scope, missing values, comparison types, and references to skipped or failed nodes.

## Relationship to Behavior Trees

Workflow IR is not BehaviorTree.CPP XML and should not be forced to mirror one runtime. Behavior-tree semantics remain a useful reference for later fallback, retry, reactivity, halting, and subtree composition. A future compiler/backend can be evaluated after RoboArc's own contracts are stable.
