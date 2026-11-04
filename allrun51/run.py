import argparse
import os
import shlex
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Sequence
from pathlib import Path
from textwrap import wrap

_wsl_keepalive: subprocess.Popen | None = None

project_source = str(Path(__file__).resolve().parent / "src")
if project_source not in sys.path:
    sys.path.insert(0, project_source)

from green.cli import SUPPORTED_USE_CASE_IDS, parse_use_case
from green.topology import demo_energy_objects


def project_python() -> str:
    environment_dir = Path(__file__).resolve().parent / ".venv"
    relative_executable = (
        Path("Scripts") / "python.exe" if os.name == "nt" else Path("bin") / "python"
    )
    local_python = environment_dir / relative_executable
    if not local_python.is_file():
        return sys.executable
    dependencies = subprocess.run(
        [str(local_python), "-c", "import pytest, ncclient, pyang"],
        check=False,
        capture_output=True,
        text=True,
    )
    return str(local_python) if dependencies.returncode == 0 else sys.executable


def pause_for_review(message: str, input_fn: Callable[[str], str]) -> None:
    try:
        input_fn(message)
    except EOFError:
        pass


def _wsl_command(project_dir: Path, shell_command: str) -> list[str]:
    if os.name == "nt":
        project_path = _wsl_project_path(project_dir)
        command = f"cd {shlex.quote(project_path)} && {shell_command}"
        return ["wsl.exe", "-e", "bash", "-lc", command]
    return ["bash", "-lc", f"cd {shlex.quote(str(project_dir))} && {shell_command}"]


def _wsl_project_path(project_dir: Path) -> str:
    if os.name == "nt":
        drive = project_dir.drive[0].lower()
        return f"/mnt/{drive}{project_dir.as_posix()[2:]}"
    return str(project_dir)


def _start_wsl_keepalive() -> bool:
    global _wsl_keepalive
    if os.name != "nt":
        return True
    if _wsl_keepalive is not None:
        if _wsl_keepalive.poll() is None:
            return True
        _wsl_keepalive = None

    try:
        _wsl_keepalive = subprocess.Popen(
            ["wsl.exe", "--exec", "/bin/cat"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as error:
        print(f"Could not keep WSL session alive: {error}")
        return False

    if _wsl_keepalive.poll() is not None:
        print("Could not keep WSL session alive: wsl.exe exited immediately.")
        _wsl_keepalive = None
        return False
    return True


def _stop_wsl_keepalive() -> None:
    global _wsl_keepalive
    process = _wsl_keepalive
    _wsl_keepalive = None
    if process is None:
        return

    try:
        if process.stdin is not None:
            process.stdin.close()
        process.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)


def _hardware_component_ties() -> list[str]:
    objects = demo_energy_objects()
    object_ids_by_name = {
        item.hardware_component_name: item.energy_object_id for item in objects
    }
    children_by_parent: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for item in objects:
        if item.hardware_parent_name and item.hardware_component_name:
            children_by_parent[item.hardware_parent_name].append(
                (item.hardware_component_name, item.energy_object_id)
            )

    lines = []
    for parent, children in sorted(children_by_parent.items()):
        child_names = ", ".join(f"{object_id}/{name}" for name, object_id in children)
        sibling_label = " [siblings]" if len(children) > 1 else ""
        parent_id = object_ids_by_name.get(parent, "unmapped")
        lines.append(f"{parent_id}/{parent} -> {child_names}{sibling_label}")
    return lines


def _print_netconf_ready(project_dir: Path) -> None:
    pid_command = (
        "printf '%s\\n' "
        "\"$(systemctl show sysrepo-plugind.service -p MainPID --value)\" "
        "\"$(systemctl show netopeer2.service -p MainPID --value)\""
    )
    try:
        result = subprocess.run(
            _wsl_command(project_dir, pid_command),
            check=False,
            capture_output=True,
            text=True,
        )
        pids = result.stdout.splitlines() if result.returncode == 0 else []
    except OSError:
        pids = []
    sysrepo_pid = pids[0].strip() if len(pids) > 0 else "unknown"
    netopeer_pid = pids[1].strip() if len(pids) > 1 else "unknown"
    print("WSL NETCONF ready (Netopeer2 TCP/830).")
    print(f"WSL service PIDs: sysrepo-plugind={sysrepo_pid}, netopeer2={netopeer_pid}.")
    ties = _hardware_component_ties()
    if ties:
        print("Hardware component ties (Energy Object ID/component; parent/siblings):")
        for tie in ties:
            for line in wrap(
                tie,
                width=88,
                subsequent_indent="    ",
                break_long_words=False,
                break_on_hyphens=False,
            ):
                print(line)


def ensure_netconf_services() -> bool:
    if not _start_wsl_keepalive():
        return False
    project_dir = Path(__file__).resolve().parent
    wsl_project = _wsl_project_path(project_dir)
    expected_environment = (
        f"SRPD_PLUGINS_PATH={wsl_project}/netconf/plugins",
        f"GREEN_NETCONF_STATE_FILE={wsl_project}/runtime/operational.json",
        f"GREEN_NETCONF_TRACE_FILE={wsl_project}/logs/netconf-trace.log",
    )
    environment_check = " && ".join(
        f"systemctl show-environment | grep -Fx {shlex.quote(value)}"
        for value in expected_environment
    )
    health_check = (
        "systemctl is-active --quiet sysrepo-plugind.service && "
        "systemctl is-active --quiet netopeer2.service && "
        "ss -ltn | awk '$4 ~ /:830$/ { found=1 } END { exit !found }' && "
        "sysrepoctl -l | awk -F'|' '$1 ~ /^ietf-power-and-energy[[:space:]]/ { found=1 } END { exit !found }' && "
        f"{environment_check}"
    )
    try:
        health = subprocess.run(
            _wsl_command(project_dir, health_check),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"NETCONF infrastructure health check failed: {error}")
        return False

    if health.returncode == 0:
        _print_netconf_ready(project_dir)
        return True

    try:
        startup = subprocess.run(
            _wsl_command(project_dir, "bash scripts/wsl-netconf-start.sh"),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"Could not start WSL NETCONF services: {error}")
        return False

    if startup.returncode != 0:
        print(f"WSL NETCONF startup failed with exit {startup.returncode}.")
        if startup.stdout.strip():
            print(startup.stdout.strip())
        if startup.stderr.strip():
            print(startup.stderr.strip())
        return False
    _print_netconf_ready(project_dir)
    return True


def stop_netconf_services() -> None:
    project_dir = Path(__file__).resolve().parent
    stop_script = project_dir / "scripts" / "wsl-netconf-stop.sh"
    if os.name == "nt":
        drive = project_dir.drive[0].lower()
        project_path = f"/mnt/{drive}{project_dir.as_posix()[2:]}"
        wsl_command = (
            f"cd {shlex.quote(project_path)} && bash scripts/wsl-netconf-stop.sh"
        )
        command = ["wsl.exe", "-e", "bash", "-lc", wsl_command]
    else:
        command = ["bash", str(stop_script)]

    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as error:
        print(f"Warning: could not stop NETCONF services: {error}")
        _stop_wsl_keepalive()
        return

    output = result.stdout.strip()
    if result.returncode == 0:
        if output:
            print(output)
        _stop_wsl_keepalive()
        return
    detail = result.stderr.strip() or output
    print(f"Warning: could not stop NETCONF services (exit {result.returncode}).")
    if detail:
        print(detail)
    _stop_wsl_keepalive()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Test and run the GREEN allrun51 simulator")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--auto", dest="auto", action="store_true", help="run all events automatically without prompts")
    mode.add_argument("--interactive", dest="auto", action="store_false", help="prompt between events (default)")
    parser.set_defaults(auto=False)
    parser.add_argument("--interval", type=float, help="automatic-mode delay in seconds (default: 1)")
    parser.add_argument(
        "-u",
        "--uc",
        type=parse_use_case,
        metavar="UC",
        help=f"run only one implemented UC (available: {', '.join(SUPPORTED_USE_CASE_IDS)})",
    )
    args = parser.parse_args(argv)
    if args.interval is not None and args.interval < 0:
        parser.error("--interval must be non-negative")

    try:
        if not ensure_netconf_services():
            print("Tests were not started because NETCONF infrastructure is unavailable.")
            return 1
        project_dir = Path(__file__).resolve().parent
        python = project_python()
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            path for path in (project_source, environment.get("PYTHONPATH", "")) if path
        )
        if args.uc is None:
            tests = subprocess.run(
                [python, "-m", "pytest", "-v"],
                check=False,
                stdin=subprocess.DEVNULL,
                cwd=project_dir,
                env=environment,
            )
            if tests.returncode != 0:
                pause_for_review("\nTests failed. Press ENTER to review the trace...", input)
                return tests.returncode
        else:
            print(
                f"Skipping full pytest suite for selected {args.uc.value}; "
                "run python -m pytest -v separately after code changes.",
                flush=True,
            )

        if args.uc is None:
            print("\nAll tests passed. Starting the GREEN runtime...\n", flush=True)
        else:
            print(f"\nStarting selected {args.uc.value}...\n", flush=True)
        runtime_command = [python, "-m", "green"]
        if args.auto:
            runtime_command.append("--auto")
        if args.interval is not None:
            runtime_command.extend(("--interval", str(args.interval)))
        if args.uc is not None:
            runtime_command.extend(("--uc", args.uc.value.removeprefix("UC ")))
        runtime = subprocess.run(runtime_command, check=False, cwd=project_dir, env=environment)
        pause_for_review("\nGREEN runtime ended. Press ENTER to review the trace...", input)
        return runtime.returncode
    finally:
        stop_netconf_services()


if __name__ == "__main__":
    raise SystemExit(main())