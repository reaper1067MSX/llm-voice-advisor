"""Unit tests for ConversationHistoryManager and ConversationHistoryPort."""

from concurrent.futures import ThreadPoolExecutor

from abi_coach.application.services.history_manager import ConversationHistoryManager
from abi_coach.domain.ports.history_port import ConversationHistoryPort


def test_history_manager_rolling_window_and_slice():
    """Verify rolling window pruning, truthiness, and slice formatting."""
    mgr = ConversationHistoryManager(max_turns=4)
    assert isinstance(mgr, ConversationHistoryPort)
    assert bool(mgr) is True
    assert len(mgr) == 0

    mgr.add_user_coach("Hola", "Saludos")
    assert len(mgr) == 2
    assert mgr[0].role == "user"

    slice_lines = mgr.get_history_slice(1)
    assert len(slice_lines) == 2
    assert slice_lines[0] == "USER: Hola"

    for i in range(10):
        mgr.record_turn("user", f"msg {i}")
    assert len(mgr) == 4
    assert mgr[-1].text == "msg 9"

    mgr.clear()
    assert len(mgr) == 0


def test_history_manager_thread_safety():
    """Verify concurrent turn recording retains window integrity."""
    mgr = ConversationHistoryManager(max_turns=8)

    def worker(worker_id: int):
        for j in range(20):
            mgr.record_turn("user", f"w{worker_id}_{j}")

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(worker, range(4)))

    assert len(mgr) == 8
