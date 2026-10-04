"""Demonstrate the three required retry-policy outcomes."""

from __future__ import annotations

from retry_policy import (
    RetryExhaustedError,
    SequenceFailureInjector,
    run_with_retry,
)


def operation() -> str:
    return "database read succeeded"


def run_success_first_attempt() -> None:
    result = run_with_retry(
        operation,
        should_fail=SequenceFailureInjector([False]),
        base_delay_seconds=0.01,
    )
    assert result.attempts == 1
    print(
        "PASS 1/3 - success on first attempt: "
        f"attempts={result.attempts}, value={result.value!r}"
    )


def run_success_after_retry() -> None:
    result = run_with_retry(
        operation,
        should_fail=SequenceFailureInjector([True, False]),
        base_delay_seconds=0.01,
    )
    assert result.attempts == 2
    print(
        "PASS 2/3 - first attempt failed, retry succeeded: "
        f"attempts={result.attempts}, value={result.value!r}"
    )


def run_clean_failure() -> None:
    try:
        run_with_retry(
            operation,
            should_fail=SequenceFailureInjector([True, True, True]),
            base_delay_seconds=0.01,
        )
    except RetryExhaustedError as error:
        response = {
            "ok": False,
            "data": None,
            "error": f"operation failed after {error.attempts} attempts",
        }
        assert error.attempts == 3
        print(
            "PASS 3/3 - all retries failed cleanly: "
            f"attempts={error.attempts}, response={response}"
        )
        return
    raise AssertionError("expected all retry attempts to fail")


def main() -> None:
    print("HW5 Part 3 retry demonstration")
    run_success_first_attempt()
    run_success_after_retry()
    run_clean_failure()
    print("Retry demonstration: 3/3 PASS")


if __name__ == "__main__":
    main()
