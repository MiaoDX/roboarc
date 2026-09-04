from pathlib import Path


def test_core_layers_have_no_ros_imports() -> None:
    for root in (Path("src/roboarc/contracts"), Path("src/roboarc/runtime")):
        for path in root.glob("*.py"):
            source = path.read_text()
            for module in ("rclpy", "roboarc_tiago", "reachy2_sdk"):
                assert module not in source, f"{path} imports robot-native module {module}"
