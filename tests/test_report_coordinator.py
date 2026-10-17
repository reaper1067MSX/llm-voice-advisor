"""Unit tests for TacticalReportToolCoordinator and ReportPresenterService."""

from pathlib import Path

from abi_coach.application.services.report_coordinator import TacticalReportToolCoordinator


def test_report_coordinator_event_dispatch(tmp_path: Path):
    """Verify report coordinator dispatches tool calls and updates last_report_path."""
    rep_dir = str(tmp_path / "reports")
    opened = []

    coordinator = TacticalReportToolCoordinator(
        output_dir=rep_dir,
        auto_open=True,
        opener=lambda p: opened.append(p),
    )
    assert coordinator.last_report_path is None

    msg = coordinator.create_report("Test Stat", "<table><tr><td>Stat</td></tr></table>")
    assert "exitosamente" in msg
    assert coordinator.last_report_path is not None
    assert Path(coordinator.last_report_path).is_file()
    assert len(opened) == 1

    cb = coordinator.create_tool_callback()
    res = cb("Callback Report", "<div>Body</div>")
    assert "exitosamente" in res
