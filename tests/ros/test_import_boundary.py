from pathlib import Path


def test_core_layers_have_no_ros_imports() -> None:
    for root in (Path("src/roboarc/contracts"), Path("src/roboarc/runtime")):
        for path in root.glob("*.py"):
            assert "rclpy" not in path.read_text()
