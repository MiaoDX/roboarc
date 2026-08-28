# Workflow IR

The Workflow IR is RoboArc's canonical representation of a robot program.

```text
Blockly workspace --compile--> Workflow IR --execute--> Runtime
```

Blockly serialization is preserved so a user can reopen an editor exactly as they left it, but editor state is not the executable contract. This keeps RoboArc open to additional authoring surfaces such as a node graph or AI-generated workflows.

## v0.1 node set

Keep the first IR deliberately small:

- `sequence`
- `if`
- `loop`
- `wait`
- `parallel`
- `capability`

Features such as `retry`, `timeout`, `fallback`, `subflow`, `event`, `guard`, and explicit resource locks are useful, but should be introduced only after the vertical slice is stable.

## Example

```json
{
  "schema_version": 1,
  "workflow": {
    "id": "welcome-visitor",
    "type": "sequence",
    "children": [
      {
        "id": "go-reception",
        "type": "capability",
        "capability": "navigation.goto",
        "args": {
          "target": "reception"
        }
      },
      {
        "id": "say-hello",
        "type": "capability",
        "capability": "speech.say",
        "args": {
          "text": "Hello!"
        }
      }
    ]
  }
}
```

Stable node IDs are important even in v0.1 because runtime events, visual highlighting, logs, and future replay need to refer to the same logical node.

## Project document

A saved project may contain both editor state and canonical IR:

```json
{
  "schema_version": 1,
  "name": "Welcome visitor",
  "editor": {
    "type": "blockly",
    "state": {}
  },
  "workflow": {}
}
```

The `editor` field is allowed to evolve independently from the workflow schema.

## Values and references

v0.1 should favor JSON-native literal values and a minimal variable/reference mechanism rather than building a general expression language immediately.

A future typed value model may need domain types such as:

- `pose`
- `map_location`
- `object_pose`
- `joint_pose`
- `image`
- `duration`

Those types should have explicit serialization and validation rules rather than being hidden inside arbitrary strings.

## Validation

Validation should happen before execution and should be able to report errors against node IDs. Initial checks should include:

- known node type;
- known capability ID;
- required inputs present;
- basic input type/range checks;
- robot profile supports the requested capability;
- structurally valid control flow;
- obvious resource conflicts in parallel branches where possible.

Validation is not a substitute for runtime safety checks in robot controllers.

## Schema evolution

Use an explicit integer `schema_version` from the first saved file. Do not build a migration framework until the schema actually changes, but require migrations to be deterministic and testable when they are introduced.

Recommended policy:

1. readers reject unsupported future major schema versions;
2. migrations transform old documents into the current canonical schema;
3. editor-specific state has its own compatibility policy;
4. runtime execution always operates on a validated current IR.

## Relationship to Behavior Trees

RoboArc's IR should not be forced to mirror BehaviorTree.CPP XML or any other runtime format. Behavior-tree semantics are a valuable reference for later fallback, retry, reactive conditions, and cancellation behavior, but the v0.1 IR should stay aligned with RoboArc's product model.

A future compiler could target a behavior-tree runtime if that becomes useful.

## AI compatibility

An editor-neutral, typed IR also creates a safer future boundary for AI-assisted authoring:

```text
Natural language -> proposed Workflow IR -> validation -> visual review -> execution
```

The model should generate the same declarative representation a human editor produces, rather than arbitrary robot-control code.
