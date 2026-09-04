"""Reachy capability contracts, independent of the vendor SDK."""

from roboarc.contracts import (
    CapabilityManifest,
    ExecutionTraits,
    ProgressMode,
    ProgressSource,
    ProgressSpec,
    RobotProfile,
    ValueSpec,
    ValueType,
)

JOINT_FIELDS = (
    "shoulder_pitch_deg",
    "shoulder_roll_deg",
    "elbow_yaw_deg",
    "elbow_pitch_deg",
    "wrist_roll_deg",
    "wrist_pitch_deg",
    "wrist_yaw_deg",
)
ARM_POSE_JOINTS = CapabilityManifest(
    id="reachy.arm.pose_joints",
    version=1,
    title="Pose arm joints",
    category="Arm",
    description="Move one Reachy arm to a deterministic seven-joint target in degrees.",
    inputs={
        "side": ValueSpec(type=ValueType.STRING, required=True, enum=("left", "right")),
        **{
            field: ValueSpec(type=ValueType.NUMBER, required=True, minimum=-180, maximum=180)
            for field in JOINT_FIELDS
        },
        "duration_ms": ValueSpec(
            type=ValueType.DURATION_MS, default=1000, minimum=0, maximum=10_000
        ),
    },
    outputs={
        "side": ValueSpec(type=ValueType.STRING, required=True),
        "completed": ValueSpec(type=ValueType.BOOLEAN, required=True),
    },
    execution=ExecutionTraits(timeout_ms=15_000, cancellable=False),
    progress=ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.ESTIMATED),
    resources=("arm_motion",),
)
ARM_GESTURE = CapabilityManifest(
    id="reachy.arm.gesture",
    version=1,
    title="Perform arm gesture",
    category="Reachy actions",
    description="Perform a named, visually meaningful Reachy arm gesture.",
    inputs={
        "gesture": ValueSpec(
            type=ValueType.STRING,
            required=True,
            enum=("home", "raise", "wave", "present"),
        ),
        "side": ValueSpec(type=ValueType.STRING, required=True, enum=("left", "right")),
        "duration_ms": ValueSpec(
            type=ValueType.DURATION_MS, default=6000, minimum=100, maximum=10_000
        ),
    },
    outputs={
        "gesture": ValueSpec(type=ValueType.STRING, required=True),
        "side": ValueSpec(type=ValueType.STRING, required=True),
        "completed": ValueSpec(type=ValueType.BOOLEAN, required=True),
    },
    execution=ExecutionTraits(timeout_ms=30_000, cancellable=False),
    progress=ProgressSpec(mode=ProgressMode.PERCENT, source=ProgressSource.ESTIMATED),
    resources=("arm_motion",),
)
REACHY_MANIFESTS = (ARM_GESTURE,)
REACHY_PROFILE = RobotProfile(
    id="reachy2-sim",
    title="Reachy 2 MuJoCo",
    adapter="reachy2-sdk",
    capabilities=(ARM_GESTURE.ref,),
)
