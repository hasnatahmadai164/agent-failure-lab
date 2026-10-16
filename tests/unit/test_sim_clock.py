import pytest

from agent_failure_lab.sim import ManualClock, SystemClock


def test_manual_clock_starts_at_the_given_time() -> None:
    assert ManualClock(start=5.0).now() == 5.0


def test_advance_moves_the_clock_forward() -> None:
    clock = ManualClock()

    clock.advance(2.5)
    clock.advance(1.5)

    assert clock.now() == 4.0


def test_sleep_advances_the_clock_without_waiting() -> None:
    clock = ManualClock()

    clock.sleep(3600)

    assert clock.now() == 3600


def test_advance_rejects_negative_time() -> None:
    with pytest.raises(ValueError, match="backwards"):
        ManualClock().advance(-1)


def test_system_clock_never_goes_backwards() -> None:
    clock = SystemClock()

    first = clock.now()
    second = clock.now()

    assert second >= first
