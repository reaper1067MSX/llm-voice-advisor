"""Unit tests for Execution Pipeline and Middlewares."""

import pytest
from abi_coach.application.pipeline import (
    ExceptionHandlingMiddleware,
    ExecutionPipeline,
    LoggingMiddleware,
    Middleware,
)
from abi_coach.domain.common.errors import DomainError, SystemUnexpectedError
from abi_coach.domain.common.result import Failure, Result, Success, fail, ok


def test_pipeline_basic_execution():
    pipeline = ExecutionPipeline()

    def sample_handler(cmd: str) -> Result:
        return ok(f"Handled: {cmd}")

    res = pipeline.execute("test_query", sample_handler)
    assert res.is_ok()
    assert res.unwrap() == "Handled: test_query"


def test_exception_handling_middleware_catches_unhandled_crash():
    exc_mw = ExceptionHandlingMiddleware()
    pipeline = ExecutionPipeline().add_middleware(exc_mw)

    def crashing_handler(cmd: str) -> Result:
        # Simulate unexpected system panic (e.g. CUDA memory explosion, C-level crash)
        raise RuntimeError("Simulated fatal GPU VRAM crash")

    res = pipeline.execute("crash_me", crashing_handler)

    assert not res.is_ok()
    assert res.is_err()
    assert isinstance(res.error, SystemUnexpectedError)
    assert "Simulated fatal GPU VRAM crash" in res.error.technical_detail
    assert "fallo temporal" in res.error.get_spoken_message()


def test_logging_middleware_measures_latency():
    log_mw = LoggingMiddleware()
    pipeline = ExecutionPipeline().add_middleware(log_mw)

    def slow_handler(cmd: str) -> Result:
        return ok("Fast result")

    res = pipeline.execute("query", slow_handler)
    assert res.is_ok()
    assert log_mw.last_latency_ms >= 0.0


def test_middleware_chain_execution_order():
    execution_order = []

    class OrderMiddleware(Middleware):
        def __init__(self, name: str):
            self.name = name

        def handle(self, command, next_handler):
            execution_order.append(f"{self.name}_start")
            res = next_handler(command)
            execution_order.append(f"{self.name}_end")
            return res

    pipeline = (
        ExecutionPipeline()
        .add_middleware(OrderMiddleware("outer"))
        .add_middleware(OrderMiddleware("inner"))
    )

    def dummy_handler(cmd):
        execution_order.append("handler")
        return ok("done")

    res = pipeline.execute("cmd", dummy_handler)
    assert res.is_ok()
    assert execution_order == [
        "outer_start",
        "inner_start",
        "handler",
        "inner_end",
        "outer_end",
    ]
