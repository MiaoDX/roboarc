from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

pytest.importorskip("rclpy", reason="ROS 2 Jazzy is required for TIAGo manual tests")
pytest.importorskip("nav2_msgs", reason="Nav2 messages are required for TIAGo manual tests")
pytest.importorskip("control_msgs", reason="control_msgs is required for TIAGo manual tests")

from .adapter import TiagoRosAdapter, _clamp, _transform_point


def test_tiago_adapter_uses_capability_adapter_boundary() -> None:
    assert any(base.__name__ == "CapabilityAdapter" for base in TiagoRosAdapter.__bases__)


def test_clamp_limits_head_joint_targets() -> None:
    assert _clamp(-2.0, -1.0, 1.0) == -1.0
    assert _clamp(0.5, -1.0, 1.0) == 0.5
    assert _clamp(2.0, -1.0, 1.0) == 1.0


def test_transform_point_applies_tf_rotation_and_translation() -> None:
    half_turn = math.sin(math.pi / 4)
    transform = SimpleNamespace(
        transform=SimpleNamespace(
            translation=SimpleNamespace(x=1.0, y=2.0, z=3.0),
            rotation=SimpleNamespace(x=0.0, y=0.0, z=half_turn, w=half_turn),
        )
    )

    assert _transform_point(transform, (1.0, 0.0, 0.0)) == pytest.approx(
        (1.0, 3.0, 3.0)
    )
