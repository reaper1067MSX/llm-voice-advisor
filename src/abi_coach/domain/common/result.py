"""Railway Oriented Programming Result Pattern for Python.

Provides generic Result[T, E], Success[T], and Failure[E] for explicit,
type-safe business error handling without unexpected exceptions.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Generic, Optional, TypeVar, Union

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


@dataclass(frozen=True)
class Success(Generic[T]):
    """Represents a successful operation carrying a payload value."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: Any) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> Success[U]:
        """Transform success value using provided function."""
        return Success(fn(self.value))

    def bind(self, fn: Callable[[T], Result[U, Any]]) -> Result[U, Any]:
        """Monadic bind (flat_map) chaining another operation that returns a Result."""
        return fn(self.value)


@dataclass(frozen=True)
class Failure(Generic[E]):
    """Represents a failed domain operation carrying an error descriptor."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def unwrap(self) -> Any:
        if isinstance(self.error, Exception):
            raise self.error
        raise ValueError(f"Called unwrap on Failure: {self.error}")

    def unwrap_or(self, default: U) -> U:
        return default

    def map(self, fn: Callable[[Any], Any]) -> Failure[E]:
        """Mapping over Failure is a no-op, preserving the error."""
        return self

    def bind(self, fn: Callable[[Any], Any]) -> Failure[E]:
        """Binding over Failure short-circuits, preserving the error."""
        return self


Result = Union[Success[T], Failure[E]]


class ResultHelper:
    """Helper namespace for creating Result instances concisely."""

    @staticmethod
    def ok(value: T) -> Success[T]:
        return Success(value)

    @staticmethod
    def fail(error: E) -> Failure[E]:
        return Failure(error)


ok = ResultHelper.ok
fail = ResultHelper.fail
