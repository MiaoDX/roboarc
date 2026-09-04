"""Deterministic fake matching the small Reachy SDK surface used by the adapter."""

from __future__ import annotations


class FakeReachyArm:
    def __init__(
        self, *, positions: tuple[float, ...] = (0.0,) * 7, fail: Exception | None = None
    ) -> None:
        self.positions = positions
        self.fail = fail
        self.targets: list[tuple[float, ...]] = []

    def get_present_positions(self) -> tuple[float, ...]:
        return self.positions

    def set_goal_positions(self, target: tuple[float, ...]) -> None:
        if self.fail is not None:
            raise self.fail
        self.positions = tuple(target)
        self.targets.append(self.positions)


class FakeReachy:
    def __init__(
        self, *, l_arm: FakeReachyArm | None = None, r_arm: FakeReachyArm | None = None
    ) -> None:
        self.l_arm = l_arm or FakeReachyArm()
        self.r_arm = r_arm or FakeReachyArm()
        self.send_count = 0

    def send_goal_positions(self) -> None:
        self.send_count += 1
