"""Backward compatibility shim for abi_coach.main -> abi_coach.entrypoints."""

from abi_coach.entrypoints.cli import (
    cmd_ask,
    cmd_list_models,
    cmd_list_voices,
    cmd_test_capture,
    cmd_test_mic,
    cmd_test_tts,
    main,
)
from abi_coach.entrypoints.loop import (
    BANNER,
    run_interactive_loop,
    should_inspect_screen,
)

__all__ = [
    "main",
    "run_interactive_loop",
    "should_inspect_screen",
    "BANNER",
    "cmd_ask",
    "cmd_list_models",
    "cmd_list_voices",
    "cmd_test_capture",
    "cmd_test_mic",
    "cmd_test_tts",
]

if __name__ == "__main__":
    main()
