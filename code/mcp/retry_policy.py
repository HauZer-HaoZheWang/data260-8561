"""Bounded timeout and exponential-backoff utilities for HW5 tools."""

from __future__ import annotations

import random
import time
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from typing import Generic, TypeVar


T = TypeVar("T")


class TransientOperationError(RuntimeError):
    """A temporary failure that may succeed on a later attempt."""


class OperationTimeout(TransientOperationError):
    """An operation exceeded its configured wall-clock timeout."""


class RetryExhaustedError(RuntimeError):
    """All bounded retry attempts failed."""

    def __init__(self, attempts: int, latency_ms: float, last_error: BaseException):
        self.attempts = attempts
        self.latency_ms = latency_ms
        self.last_error = last_error
        super().__init__(
            f"operation failed after {attempts} attempts: {last_error}"
        )


@dataclass(frozen=True)
class RetryOutcome(Generic[T]):
    """A successful value plus retry metadata."""

    value: T
    attempts: int
    latency_ms: float


class SeededFailureInjector:
    """Generate a reproducible transient-failure sequence."""

    def __init__(self, failure_rate: float, seed: int):
        if not 0.0 <= failure_rate <= 1.0:
            raise ValueError("failure_rate must be between 0 and 1")
        self.failure_rate = failure_rate
        self._random = random.Random(seed)

    def __call__(self, attempt: int) -> bool:
        del attempt
        return self._random.random() < self.failure_rate


class SequenceFailureInjector:
    """Return a prescribed failure sequence for demonstrations and tests."""

    def __init__(self, failures: Sequence[bool]):
        self._failures = iter(failures)

    def __call__(self, attempt: int) -> bool:
        del attempt
        return next(self._failures, False)


def _call_with_timeout(operation: Callable[[], T], timeout_seconds: float) -> T:
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="hw5-operation")
    future = executor.submit(operation)
    timed_out = False
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as error:
        timed_out = True
        future.cancel()
        raise OperationTimeout(
            f"operation exceeded {timeout_seconds:.3f} seconds"
        ) from error
    finally:
        executor.shutdown(wait=not timed_out, cancel_futures=True)


def run_with_retry(
    operation: Callable[[], T],
    *,
    timeout_seconds: float = 2.0,
    max_attempts: int = 3,
    base_delay_seconds: float = 0.05,
    max_delay_seconds: float = 0.20,
    retryable_exceptions: tuple[type[BaseException], ...] = (
        TransientOperationError,
    ),
    should_fail: Callable[[int], bool] | None = None,
    on_retry: Callable[[int, BaseException, float], None] | None = None,
) -> RetryOutcome[T]:
    """Run an operation with a timeout and bounded exponential backoff."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if base_delay_seconds < 0 or max_delay_seconds < 0:
        raise ValueError("backoff delays cannot be negative")

    started = time.perf_counter()
    caught_exceptions = retryable_exceptions + (OperationTimeout,)

    for attempt in range(1, max_attempts + 1):
        try:
            if should_fail is not None and should_fail(attempt):
                raise TransientOperationError(
                    f"simulated transient failure on attempt {attempt}"
                )
            value = _call_with_timeout(operation, timeout_seconds)
            latency_ms = (time.perf_counter() - started) * 1000.0
            return RetryOutcome(value, attempt, latency_ms)
        except caught_exceptions as error:
            latency_ms = (time.perf_counter() - started) * 1000.0
            if attempt == max_attempts:
                raise RetryExhaustedError(attempt, latency_ms, error) from error

            delay = min(
                max_delay_seconds,
                base_delay_seconds * (2 ** (attempt - 1)),
            )
            if on_retry is not None:
                on_retry(attempt, error, delay)
            time.sleep(delay)

    raise AssertionError("retry loop ended unexpectedly")
