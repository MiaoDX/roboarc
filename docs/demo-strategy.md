# Demo Strategy

RoboArc should prove its programming model before taking on the operational complexity of a real robot. The demo strategy therefore has three layers: a first-class mock robot, a reference mobile manipulator simulation, and a second robot that demonstrates portability.

## 1. MockAdapter: required for v0.1

The mock robot is part of the product, not just a test fixture.

It should implement a representative capability set with deterministic timing and configurable success/failure behavior. This lets contributors clone RoboArc and exercise the full authoring/runtime path without ROS, Gazebo, GPU drivers, or robot hardware.

Example capabilities:

```text
navigation.goto
navigation.stop
head.look_at
speech.say
manipulation.pick
manipulation.place
perception.detect_object
```

A mock run should still produce realistic stage/progress events so the runtime UI can be developed independently.

## 2. Observable simulation loop and TIAGo reference integration

The first user-visible simulation milestone should prove the complete flow
before requiring a full robot stack. A deterministic state source should feed
Runtime events and robot telemetry into a Rerun trace that can be opened in a
Web Viewer or standalone viewer. The Workbench remains the control and status
surface; the viewer is external by default.

TIAGo is the first ROS-native integration after that loop is proven:

TIAGo is the leading first real simulation because its public ROS 2 simulation combines the capability breadth needed to make visual programming interesting:

- mobile navigation;
- SLAM;
- head and joint control;
- manipulation;
- MoveIt 2;
- Gazebo simulation.

PAL Robotics documents launching TIAGo simulation together with Nav2 and MoveIt 2, which makes it a useful integration target without first building a robot stack from scratch.

Reference: https://github.com/pal-robotics/tiago_simulation

### Candidate demo workflows

**Welcome visitor**

```text
Go to Reception
-> Wait for person
-> Look at person
-> Say "Welcome!"
-> Gesture
```

**Patrol**

```text
Repeat
  Go to Reception
  Look around
  Go to Kitchen
  Look around
```

**Fetch object**

```text
Go to Table
-> Detect object
-> Pick
-> Go to Drop Zone
-> Place
```

The first TIAGo milestone does not need all three. Navigation + head + speech is enough to validate the adapter boundary before adding manipulation.

## 3. Reachy 2: selected portability/showcase target

Reachy 2 is a strong second robot because its software stack exposes a modern Python SDK and gRPC/ROS 2 bridge, while its MuJoCo ecosystem includes mobile-base, arm, camera, and manipulation-oriented scenes.

Useful upstream projects:

- https://github.com/pollen-robotics/reachy2-sdk
- https://github.com/pollen-robotics/reachy2_core
- https://github.com/pollen-robotics/reachy2_mujoco
- https://github.com/pollen-robotics/reachy2_mujoco_assets
- https://github.com/pollen-robotics/reachy2-tutorials

The tutorials explicitly support running examples against MuJoCo as well as the real robot. The MuJoCo assets include table, fruit-sorting, and kitchen scenes.

Reachy 2 is particularly valuable for demonstrating that RoboArc does not require ROS-facing capability handlers: the adapter can target the higher-level SDK.

For v0.3, the official Docker image's MuJoCo + SDK server path is the product
proof. Its browser display is recorded into the same manifest-backed,
time-aligned review workflow used for TIAGo. The official Gazebo/RViz path
remains available for engineering diagnosis but is not a second v0.3 product
lane. The image and dependencies must be pinned, and real Reachy hardware is not
required.

The Reachy adapter registers only capabilities it actually supports. Its demo
does not need to reproduce the TIAGo workflow: portability is demonstrated by
using the same RoboArc contracts and observable execution path with a
profile-appropriate capability set.

## Why not start with TurtleBot?

TurtleBot is excellent for Nav2 smoke tests and CI, but its capability surface makes the product look primarily like a navigation Blockly tool. RoboArc benefits from a hero demo with navigation plus interaction and manipulation.

A lightweight TurtleBot adapter may still be useful later as a minimal ROS/Nav2 reference.

## Why not start with a quadruped?

Quadrupeds produce compelling demos, but open simulation/control stacks often add locomotion-controller and model-tuning risk unrelated to RoboArc's core thesis. They are better showcase targets after the workflow/runtime boundary is stable.

## Simulator selection

### Gazebo

Prefer Gazebo when validating ROS-native integration, Nav2, MoveIt 2, sensors, and controller behavior. TIAGo's public simulation already follows this route.

### MuJoCo

Prefer MuJoCo when a robot ecosystem provides a high-level SDK-backed simulator and manipulation-oriented assets, as Reachy 2 does. It is also attractive for headless automated scenarios.

### Webots / Isaac Sim

Keep these as future adapter/integration possibilities rather than v0.x dependencies. RoboArc should not couple its IR or runtime to any simulator.

## CI strategy

Use a test pyramid:

1. **always-on:** IR/schema/runtime tests with MockAdapter;
2. **light integration:** adapter contract tests with fakes/stubs;
3. **scheduled/manual:** headless simulator scenarios where practical;
4. **hardware:** optional robot-specific tests outside the core CI requirement.

A contributor should not need to install a robotics simulator to run the core test suite.
