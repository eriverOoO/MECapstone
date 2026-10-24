"""Acknowledgement-driven controller. No GPIO, serial, or implicit completion."""
import time
from typing import Protocol
from .models import Action, Command, Observation, Status
from .vision.temporal import Stabilizer


class Actuator(Protocol):
    def submit(self, command: Command) -> None: ...
    def poll(self) -> tuple[int, bool] | None: ...


class MockActuator:
    def __init__(self):
        self.pending: Command | None = None
        self.events: list[tuple[int, bool]] = []

    def submit(self, command: Command) -> None:
        if self.pending is not None:
            raise RuntimeError("An actuator command is already pending")
        self.pending = command

    def complete(self, success: bool = True) -> None:
        """Explicit simulation event; never implies the video itself has changed."""
        if self.pending:
            self.events.append((self.pending.command_id, success))
            self.pending = None

    def poll(self) -> tuple[int, bool] | None:
        return self.events.pop(0) if self.events else None

    def clear(self) -> None:
        self.pending = None
        self.events.clear()


class Controller:
    def __init__(self, cfg: dict, frames: int):
        self.cfg = cfg
        self.stabilizer = Stabilizer(frames)
        self.serial = 0
        self.reset()

    def reset(self) -> None:
        """Start another mock cycle. Hardware integration needs an abort handshake."""
        self.state = "WAITING_FOR_CARD"
        self.stable = Status.UNKNOWN
        self.pending: Command | None = None
        self.last_command: Command | None = None
        self.reason = "waiting_for_card"
        self.flips = self.rotations = self.rechecks = 0
        self.last_frame = -1
        self.pending_since = None
        self.observation_since = None
        self.rotated = False
        self.stabilizer.reset()

    @property
    def next_action(self) -> str:
        if self.pending:
            return self.pending.action.value
        if self.state == "ERROR":
            return Action.ERROR.value
        if self.state == "COMPLETED":
            return "NONE"
        return Action.RECHECK.value

    def fail(self, reason: str) -> None:
        self.state, self.reason = "ERROR", reason
        self.pending = None
        self.stabilizer.reset()
        self.stable = Status.UNKNOWN

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        if self.pending and now-self.pending_since > self.cfg["action_timeout_seconds"]:
            self.fail("actuator_timeout")
        elif self.observation_since is not None and self.state not in ("ERROR","COMPLETED") and not self.pending:
            if now-self.observation_since > self.cfg["observation_timeout_seconds"]:
                self.fail("observation_timeout")

    def observe(self, obs: Observation, now: float | None = None) -> Command | None:
        now = time.monotonic() if now is None else now
        self.tick(now)
        if self.state in ("ERROR", "COMPLETED"):
            return None
        # Repeated UI redraws and out-of-order observations never add evidence.
        if obs.frame <= self.last_frame:
            return None
        self.last_frame = obs.frame
        if self.pending:
            return None
        if not obs.card_detected:
            self.stabilizer.reset()
            self.stable = Status.UNKNOWN
            if self.flips or self.rotations:
                self.rechecks += 1
                self.reason = "card_missing_during_verification"
                if self.rechecks >= self.cfg["max_recheck_frames"]:
                    self.fail("verification_frame_limit")
            else:
                self.state = "WAITING_FOR_CARD"
                # Keep timeout active once a cycle began, even if the card disappears.
            return None
        if self.observation_since is None:
            self.observation_since = now
        self.state = "VERIFYING" if self.flips or self.rotations else "ANALYZING"
        self.stable = self.stabilizer.update(obs.status)
        self.reason = obs.reason
        self.rechecks += 1
        if self.rechecks >= self.cfg["max_recheck_frames"]:
            self.fail("verification_frame_limit")
            return None
        if self.stable == Status.UNKNOWN:
            return None
        if self.stable == Status.CHIP_NOT_VISIBLE:
            if self.flips >= self.cfg["max_flips"] or self.rotated:
                self.fail("chip_still_not_visible")
                return None
            self.flips += 1
            action, state = Action.FLIP, "FLIPPING"
        elif self.stable == Status.REVERSED:
            if self.rotations >= self.cfg["max_rotations"]:
                self.fail("rotation_verification_failed")
                return None
            self.rotations += 1
            action, state = Action.ROTATE_180, "ROTATING"
        else:
            action, state = Action.INSERT, "INSERTING"
        self.serial += 1
        self.pending = Command(self.serial,self.stable,action,action != Action.INSERT)
        self.last_command = self.pending
        self.pending_since = now
        self.state = state
        self.observation_since = None
        return self.pending

    def acknowledge(self, command_id: int, success: bool, now: float | None = None) -> bool:
        now = time.monotonic() if now is None else now
        self.tick(now)
        if self.pending is None or command_id != self.pending.command_id:
            return False
        action = self.pending.action
        self.pending, self.pending_since = None, None
        self.stabilizer.reset()
        self.stable = Status.UNKNOWN
        if not success:
            self.fail("actuator_reported_failure")
        elif action == Action.INSERT:
            self.state, self.reason = "COMPLETED", "insert_acknowledged"
        else:
            self.rotated = self.rotated or action == Action.ROTATE_180
            self.state, self.reason = "VERIFYING", "new_frames_required_after_ack"
            self.rechecks = 0
            self.observation_since = now
        return True
