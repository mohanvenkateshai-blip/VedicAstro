"""Canonical immutable ownership helpers for research artifacts."""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel


class FrozenDict(dict):
    """A JSON-serializable dictionary that rejects all mutation."""

    def _immutable(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("research artifact is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenDict:
        return self


class FrozenList(list):
    """A JSON-serializable list that rejects all mutation."""

    def _immutable(self, *_args: Any, **_kwargs: Any) -> None:
        raise TypeError("research artifact is immutable")

    __setitem__ = _immutable
    __delitem__ = _immutable
    append = _immutable
    clear = _immutable
    extend = _immutable
    insert = _immutable
    pop = _immutable
    remove = _immutable
    reverse = _immutable
    sort = _immutable
    __iadd__ = _immutable
    __imul__ = _immutable

    def __deepcopy__(self, memo: dict[int, Any]) -> FrozenList:
        return self


def freeze_json(value: Any) -> Any:
    """Take canonical ownership of a JSON-like value and freeze it recursively."""

    if isinstance(value, dict):
        return FrozenDict({str(key): freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenList(freeze_json(item) for item in value)
    return copy.deepcopy(value)


def snapshot_model[ModelT: BaseModel](value: ModelT) -> ModelT:
    """Detach a Pydantic model from caller-owned nested objects."""

    restored = type(value).model_validate_json(value.model_dump_json())
    return _freeze_model(restored)


def _freeze_model[ModelT: BaseModel](value: ModelT) -> ModelT:
    for field_name in type(value).model_fields:
        object.__setattr__(value, field_name, _freeze_value(getattr(value, field_name)))
    return value


def _freeze_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _freeze_model(value)
    if isinstance(value, dict):
        return FrozenDict({str(key): _freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return FrozenList(_freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze_value(item) for item in value)
    return value
