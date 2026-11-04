from pathlib import Path

from green.netconf_bridge import set_netconf_trace_enabled, write_operational_snapshot
from green.simulator import generate_events


def test_trace_mode_logs_all_group_a_runtime_snapshots(monkeypatch, tmp_path: Path):
    runtime_dir = Path(__file__).parents[1] / "runtime"
    snapshot_path = runtime_dir / f"trace-test-{tmp_path.name}.json"
    trace_path = Path(__file__).parents[1] / "logs" / f"trace-test-{tmp_path.name}.log"
    monkeypatch.setenv("GREEN_NETCONF_TRACE_FILE", str(trace_path))
    set_netconf_trace_enabled(True, snapshot_path)
    try:
        events = generate_events()
        for event in events:
            write_operational_snapshot(event, snapshot_path)
        trace = trace_path.read_text(encoding="utf-8")
    finally:
        set_netconf_trace_enabled(False, snapshot_path)
        trace_path.unlink(missing_ok=True)
        snapshot_path.unlink(missing_ok=True)
        Path(f"{snapshot_path}.netconf-context").unlink(missing_ok=True)
        Path(f"{snapshot_path}.netconf-trace-enabled").unlink(missing_ok=True)

        assert len(events) == 122
        assert trace.count("operation: runtime snapshot") == 122
    for event in events:
        assert event.sequence in trace
        assert f"{event.series.value} - " in trace
    assert "UC 2.16 - Network-level Cross Layer Energy Saving | U16-9" in trace
