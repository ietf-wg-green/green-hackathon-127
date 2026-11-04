from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from green.__main__ import main, run_demo
from green.simulator import EventSimulator
import run


def run_with_commands(commands: list[str], **kwargs):
    command_iterator = iter(commands)
    output: list[str] = []
    sleep_calls: list[float] = []
    run_demo(
        EventSimulator(),
        auto=False,
        interval=1.0,
        input_fn=lambda: next(command_iterator),
        sleep_fn=sleep_calls.append,
        output_fn=output.append,
        **kwargs,
    )
    return output, sleep_calls


def event_lines(output: list[str]) -> list[str]:
    return [line for line in output if line.startswith("[UC ")]


def test_enter_advances_exactly_one_group_a_event() -> None:
    output, sleep_calls = run_with_commands(["", "q"], snapshot_fn=None)
    assert event_lines(output) == ["[UC 2.1 / U1-0] LEGACY_BASELINE"]
    assert any(line.startswith("HW     ") for line in output)
    assert any(line.startswith("ENERGY ") for line in output)
    assert any(line.startswith("REL    ") for line in output)
    assert any(line.startswith("DIFF   ") for line in output)
    assert not any(len(line) >= 79 and set(line) == {"-"} for line in output)
    assert sleep_calls == []


def test_a_runs_remaining_events_across_all_uc_boundaries() -> None:
    output, sleep_calls = run_with_commands(["", "a"], snapshot_fn=None)
    events = event_lines(output)
    assert len(events) == 122
    assert events[0] == "[UC 2.1 / U1-0] LEGACY_BASELINE"
    assert events[-1] == "[UC 2.16 / U16-9] RESTORE_DEPENDENCY_CONFIRMED"
    assert len(sleep_calls) == 120
    assert "Group A completed: 14 use cases" in output
    assert "Group B deferred: 2 use cases" in output
    assert sum(line.startswith("--- UC ") for line in output) == 14
    assert sum(" complete -> UC " in line for line in output) == 13


def test_q_exits_without_advancing() -> None:
    output, _ = run_with_commands(["q"], snapshot_fn=None)
    assert "GREEN allrun51 demo stopped." in output
    assert event_lines(output) == []


def test_d_toggles_trace_without_advancing_event() -> None:
    states: list[bool] = []
    commands = iter(["d", "", "d", "q"])
    output: list[str] = []
    run_demo(
        EventSimulator(),
        auto=False,
        interval=0,
        input_fn=lambda: next(commands),
        sleep_fn=lambda _: None,
        output_fn=output.append,
        snapshot_fn=None,
        trace_fn=lambda enabled: states.append(enabled) or Path("trace.log"),
    )
    assert states == [True, False]
    assert event_lines(output) == ["[UC 2.1 / U1-0] LEGACY_BASELINE"]
    assert any("NETCONF trace enabled" in line for line in output)
    assert any("NETCONF trace disabled" in line for line in output)


def test_r_resets_catalog_state_and_restarts_at_uc21() -> None:
    output, _ = run_with_commands(["", "r", "", "q"], snapshot_fn=None)
    assert event_lines(output) == [
        "[UC 2.1 / U1-0] LEGACY_BASELINE",
        "[UC 2.1 / U1-0] LEGACY_BASELINE",
    ]
    assert "All Group A state reset to UC 2.1 / U1-0." in output


def test_human_and_raw_views_do_not_advance_the_event() -> None:
    commands = iter(["", "summary", "relationships", "json", "xml", "diff", "q"])
    output: list[str] = []
    run_demo(
        EventSimulator(),
        auto=False,
        interval=0,
        input_fn=lambda: next(commands),
        sleep_fn=lambda _: None,
        output_fn=output.append,
        snapshot_fn=None,
        xml_fn=lambda: "<rpc-reply><data/></rpc-reply>",
    )
    assert event_lines(output) == ["[UC 2.1 / U1-0] LEGACY_BASELINE"]
    assert any("1. HARDWARE INVENTORY" in line for line in output)
    assert any("3. ENERGY RELATIONSHIPS" in line for line in output)
    assert any('"ietf-power-and-energy:energy-objects"' in line for line in output)
    assert "<rpc-reply><data/></rpc-reply>" in output
    assert any("No previous event" in line for line in output)


def test_auto_main_runs_every_event_and_writes_every_snapshot() -> None:
    output: list[str] = []
    snapshots = []
    trace_states: list[bool] = []
    main(
        ["--auto", "--interval", "0"],
        input_fn=lambda: (_ for _ in ()).throw(AssertionError("auto requested input")),
        sleep_fn=lambda _: None,
        output_fn=output.append,
        snapshot_fn=snapshots.append,
        trace_fn=lambda enabled: trace_states.append(enabled) or Path("trace.log"),
    )
    assert len(event_lines(output)) == 122
    assert len(snapshots) == 122
    assert snapshots[0].sequence == "U1-0"
    assert snapshots[-1].sequence == "U16-9"
    assert trace_states == [False]


def test_launcher_prefers_project_virtualenv(tmp_path: Path, monkeypatch) -> None:
    environment_dir = tmp_path / ".venv"
    local_python = environment_dir / (
        Path("Scripts") / "python.exe" if run.os.name == "nt" else Path("bin") / "python"
    )
    local_python.parent.mkdir(parents=True)
    local_python.touch()
    monkeypatch.setattr(run, "__file__", str(tmp_path / "run.py"))
    monkeypatch.setattr(run.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=0))
    assert run.project_python() == str(local_python)


def test_launcher_falls_back_when_project_virtualenv_lacks_dependencies(tmp_path: Path, monkeypatch) -> None:
    environment_dir = tmp_path / ".venv"
    local_python = environment_dir / (
        Path("Scripts") / "python.exe" if run.os.name == "nt" else Path("bin") / "python"
    )
    local_python.parent.mkdir(parents=True)
    local_python.touch()
    monkeypatch.setattr(run, "__file__", str(tmp_path / "run.py"))
    monkeypatch.setattr(run.subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(returncode=1))

    assert run.project_python() == sys.executable


@pytest.mark.parametrize(
    ("test_returncode", "runtime_returncode", "expected_returncode"),
    [(0, 0, 0), (0, 3, 3), (2, None, 2)],
)
def test_launcher_stops_services_on_every_exit(
    monkeypatch,
    test_returncode: int,
    runtime_returncode: int | None,
    expected_returncode: int,
) -> None:
    commands: list[list[str]] = []
    steps: list[str] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        if "pytest" in command:
            steps.append("pytest")
            return SimpleNamespace(returncode=test_returncode)
        if "green" in command:
            steps.append("runtime")
            return SimpleNamespace(returncode=runtime_returncode)
        steps.append("stop")
        return SimpleNamespace(returncode=0, stdout="stopped", stderr="")

    monkeypatch.setattr(run, "project_python", lambda: "project-python")
    monkeypatch.setattr(run, "ensure_netconf_services", lambda: steps.append("start") or True)
    monkeypatch.setattr(run.subprocess, "run", fake_run)
    monkeypatch.setattr(run, "pause_for_review", lambda *_args: None)
    assert run.main([]) == expected_returncode
    assert steps[0] == "start" and steps[-1] == "stop"
    assert commands[-1][0] == "wsl.exe"
    assert "scripts/wsl-netconf-stop.sh" in commands[-1][-1]
    runtime_commands = [command for command in commands if "green" in command]
    assert len(runtime_commands) == int(test_returncode == 0)
    if runtime_commands:
        assert runtime_commands[0] == ["project-python", "-m", "green"]


def test_launcher_does_not_run_pytest_if_wsl_startup_fails(monkeypatch) -> None:
    stop_calls: list[str] = []

    def unexpected_subprocess(*_args, **_kwargs):
        raise AssertionError("pytest/runtime must not run when NETCONF startup fails")

    monkeypatch.setattr(run, "ensure_netconf_services", lambda: False)
    monkeypatch.setattr(run, "stop_netconf_services", lambda: stop_calls.append("stop"))
    monkeypatch.setattr(run.subprocess, "run", unexpected_subprocess)

    assert run.main([]) == 1
    assert stop_calls == ["stop"]


def test_launcher_defaults_to_interactive_runtime(monkeypatch) -> None:
    commands: list[list[str]] = []
    working_directories: list[Path | None] = []
    runtime_pythonpaths: list[str] = []

    def fake_run(command: list[str], **kwargs):
        commands.append(command)
        working_directories.append(kwargs.get("cwd"))
        if "green" in command:
            runtime_pythonpaths.append(kwargs["env"]["PYTHONPATH"])
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run, "project_python", lambda: "project-python")
    monkeypatch.setattr(run, "ensure_netconf_services", lambda: True)
    monkeypatch.setattr(run.subprocess, "run", fake_run)
    monkeypatch.setattr(run, "pause_for_review", lambda *_args: None)

    assert run.main([]) == 0
    assert commands[0] == ["project-python", "-m", "pytest", "-v"]
    assert commands[1] == ["project-python", "-m", "green"]
    project_dir = Path(run.__file__).resolve().parent
    assert working_directories[:2] == [project_dir, project_dir]
    assert runtime_pythonpaths[0].split(run.os.pathsep)[0] == run.project_source


def test_launcher_auto_mode_can_run_without_delay(monkeypatch) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run, "project_python", lambda: "project-python")
    monkeypatch.setattr(run, "ensure_netconf_services", lambda: True)
    monkeypatch.setattr(run.subprocess, "run", fake_run)
    monkeypatch.setattr(run, "pause_for_review", lambda *_args: None)

    assert run.main(["--auto", "--interval", "0"]) == 0
    assert commands[1] == [
        "project-python", "-m", "green", "--auto", "--interval", "0.0"
    ]


def test_launcher_passes_selected_uc_to_runtime(monkeypatch, capsys) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(run, "project_python", lambda: "project-python")
    monkeypatch.setattr(run, "ensure_netconf_services", lambda: True)
    monkeypatch.setattr(run.subprocess, "run", fake_run)
    monkeypatch.setattr(run, "pause_for_review", lambda *_args: None)

    assert run.main(["-u", "2.13", "--auto", "--interval", "0"]) == 0
    stop_command = run._wsl_command(
        Path(run.__file__).resolve().parent,
        "bash scripts/wsl-netconf-stop.sh",
    )
    assert commands == [
        [
            "project-python", "-m", "green", "--auto", "--interval", "0.0",
            "--uc", "2.13",
        ],
        stop_command,
    ]
    output = capsys.readouterr().out
    assert "Skipping full pytest suite for selected UC 2.13" in output
    assert "All tests passed" not in output


def test_allrun51_netconf_ready_display_includes_process_pids_and_siblings(monkeypatch, capsys) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_kwargs):
        commands.append(command)
        if "systemctl is-active" in command[-1]:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if "wsl-netconf-start.sh" in command[-1]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="101\n202\n", stderr="")

    monkeypatch.setattr(run.subprocess, "run", fake_run)
    monkeypatch.setattr(run, "_start_wsl_keepalive", lambda: True)

    assert run.ensure_netconf_services()
    output = capsys.readouterr().out
    assert "WSL NETCONF ready (Netopeer2 TCP/830)." in output
    assert "WSL service PIDs: sysrepo-plugind=101, netopeer2=202." in output
    assert "eo-router-a/router-A" in output
    assert "eo-router-a-linecard-1/linecard-1" in output
    assert "eo-router-a-linecard-2/linecard-2" in output
    assert "[siblings]" in output
    assert any("sysrepo-plugind.service" in command[-1] for command in commands)


def test_windows_netconf_run_holds_and_releases_wsl_session(monkeypatch) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []
    lifecycle: list[str] = []

    class FakeStdin:
        def close(self) -> None:
            lifecycle.append("stdin-closed")

    class FakeProcess:
        stdin = FakeStdin()

        def poll(self) -> None:
            return None

        def wait(self, timeout: float) -> None:
            lifecycle.append(f"waited-{timeout}")

    process = FakeProcess()

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        calls.append((command, kwargs))
        return process

    monkeypatch.setattr(run, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(run, "_wsl_keepalive", None)
    monkeypatch.setattr(run.subprocess, "Popen", fake_popen)

    assert run._start_wsl_keepalive()
    assert calls == [
        (
            ["wsl.exe", "--exec", "/bin/cat"],
            {
                "stdin": run.subprocess.PIPE,
                "stdout": run.subprocess.DEVNULL,
                "stderr": run.subprocess.DEVNULL,
                "creationflags": getattr(run.subprocess, "CREATE_NO_WINDOW", 0),
            },
        )
    ]

    run._stop_wsl_keepalive()
    assert lifecycle == ["stdin-closed", "waited-5"]
    assert run._wsl_keepalive is None
