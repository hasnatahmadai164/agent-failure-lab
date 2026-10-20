import pytest

from agent_failure_lab.sim import SharedStore


def test_reads_and_writes_take_effect_immediately_outside_a_batch() -> None:
    store = SharedStore({"tags": []})

    store.set("tags", ["urgent"])

    assert store.get("tags") == ["urgent"]


def test_a_missing_key_returns_the_default() -> None:
    assert SharedStore().get("tags", []) == []


def test_inside_a_batch_reads_see_the_data_as_it_was_when_the_batch_began() -> None:
    store = SharedStore({"tags": []})
    store.begin()

    store.set("tags", ["urgent"])

    assert store.get("tags") == []


def test_writes_are_applied_when_the_batch_ends() -> None:
    store = SharedStore({"tags": []})
    store.begin()
    store.set("tags", ["urgent"])

    store.end()

    assert store.get("tags") == ["urgent"]


def test_two_read_modify_write_calls_in_a_batch_lose_one_update() -> None:
    store = SharedStore({"tags": []})
    store.begin()
    for tag in ("urgent", "billing"):
        store.set("tags", [*store.get("tags"), tag])
    store.end()

    assert store.get("tags") == ["billing"]
    assert store.lost_updates == 1


def test_writes_to_different_keys_in_a_batch_are_all_kept() -> None:
    store = SharedStore()
    store.begin()
    store.set("a", 1)
    store.set("b", 2)
    store.end()

    assert store.as_dict() == {"a": 1, "b": 2}
    assert store.lost_updates == 0


def test_changing_a_value_that_was_read_does_not_change_the_store() -> None:
    store = SharedStore({"tags": ["urgent"]})

    store.get("tags").append("billing")

    assert store.get("tags") == ["urgent"]


def test_the_initial_data_is_copied() -> None:
    initial = {"tags": ["urgent"]}
    store = SharedStore(initial)

    initial["tags"].append("billing")

    assert store.get("tags") == ["urgent"]


def test_opening_a_second_batch_is_an_error() -> None:
    store = SharedStore()
    store.begin()

    with pytest.raises(RuntimeError, match="already open"):
        store.begin()


def test_ending_a_batch_that_was_never_opened_is_an_error() -> None:
    with pytest.raises(RuntimeError, match="no batch"):
        SharedStore().end()
