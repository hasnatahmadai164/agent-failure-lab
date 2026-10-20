import copy
from collections.abc import Mapping
from typing import Any, Protocol


class BatchScope(Protocol):
    """Something that treats the tool calls of one model turn as a single concurrent batch."""

    def begin(self) -> None: ...

    def end(self) -> None: ...


class SharedStore:
    """A key-value store that behaves like concurrent callers while a batch is open.

    Inside a batch every read sees the data as it was when the batch began, and writes are
    held back and applied together when it ends, in call order. Two calls that each read a
    value and write it back therefore overwrite each other: the later write wins and the
    earlier update is lost. Outside a batch, reads and writes take effect immediately.
    """

    def __init__(self, initial: Mapping[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = copy.deepcopy(dict(initial or {}))
        self._snapshot: dict[str, Any] | None = None
        self._pending: list[tuple[str, Any]] = []
        self.lost_updates = 0

    def get(self, key: str, default: Any = None) -> Any:
        source = self._data if self._snapshot is None else self._snapshot
        return copy.deepcopy(source.get(key, default))

    def set(self, key: str, value: Any) -> None:
        if self._snapshot is None:
            self._data[key] = copy.deepcopy(value)
        else:
            self._pending.append((key, copy.deepcopy(value)))

    def as_dict(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def begin(self) -> None:
        if self._snapshot is not None:
            raise RuntimeError("a batch is already open")
        self._snapshot = copy.deepcopy(self._data)
        self._pending = []

    def end(self) -> None:
        if self._snapshot is None:
            raise RuntimeError("no batch is open")
        writes_per_key: dict[str, int] = {}
        for key, value in self._pending:
            self._data[key] = value
            writes_per_key[key] = writes_per_key.get(key, 0) + 1
        self.lost_updates += sum(count - 1 for count in writes_per_key.values())
        self._snapshot = None
        self._pending = []
