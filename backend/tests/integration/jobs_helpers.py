"""Top-level functions used by RQ-backed integration tests.

RQ pickles the function reference for the worker, so the target callable must be
importable by name. Lambdas, closures, and methods of test classes do not work.
"""

from __future__ import annotations


def add(a: int, b: int) -> int:
    return a + b


def explode() -> None:
    raise RuntimeError("intentional failure for tests")


def echo_kwargs(**kwargs: object) -> dict[str, object]:
    return dict(kwargs)
