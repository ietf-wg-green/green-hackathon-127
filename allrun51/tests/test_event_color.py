from green.cli import _display_event
from green.simulator import EventSimulator
from green.topology import build_demo_topology


def test_event_header_is_green_only_for_terminal_output(monkeypatch, capsys) -> None:
    event = EventSimulator().next_event()
    assert event is not None
    topology, _ = build_demo_topology(relationships=event.relationships)
    output: list[str] = []

    monkeypatch.setattr("green.cli.sys.stdout.isatty", lambda: True)
    _display_event(event, None, topology, print, None)

    monkeypatch.setattr("green.cli.sys.stdout.isatty", lambda: False)
    _display_event(event, None, topology, output.append, None)

    terminal_lines = capsys.readouterr().out.splitlines()
    assert output[0].startswith("[UC 2.1 / U1-0]")
    assert "\x1b[32m" not in output[0]
    assert terminal_lines[0].startswith("\x1b[32m[UC 2.1 / U1-0]")
    assert terminal_lines[0].endswith("\x1b[0m")
    assert "\x1b[32m" not in terminal_lines[1]
