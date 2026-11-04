import argparse
import sys
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from green.accounting import AccountingEngine
from green.catalog import EVENT_CATALOG, UC_CATALOG, USE_CASES_BY_SERIES
from green.models import AccountingResult, EventSeries, SimulatedEvent
from green.netconf_bridge import set_netconf_trace_enabled, write_operational_snapshot
from green.netconf_trace import NetconfTraceTailer
from green.simulator import EventSimulator
from green.topology import RelationshipGraph, build_demo_topology
from green.views import (
    event_to_yang,
    fetch_netconf_xml,
    render_json,
    render_compact_event,
    render_relationship_diff,
    render_relationships,
    render_summary,
    filter_yang_instance_to_energy_objects,
)

_VIEW_COMMANDS = {"summary", "relationships", "json", "xml", "diff"}
SUPPORTED_USE_CASE_IDS = tuple(
    sorted(
        {series.value.removeprefix("UC ") for series in EventSeries},
        key=lambda value: tuple(int(part) for part in value.split(".")),
    )
)


def parse_use_case(value: str) -> EventSeries:
    normalized = value.strip().upper()
    if normalized.startswith("UC"):
        normalized = normalized[2:].strip()
    normalized = normalized.replace(" ", "")
    for series in EventSeries:
        if series.value.removeprefix("UC ").replace(" ", "") == normalized:
            return series
    available = ", ".join(SUPPORTED_USE_CASE_IDS)
    raise argparse.ArgumentTypeError(
        f"unknown UC {value!r}; choose one of: {available}"
    )


def run_demo(
    simulator: EventSimulator,
    *,
    auto: bool,
    interval: float,
    input_fn: Callable[[], str],
    sleep_fn: Callable[[float], None],
    output_fn: Callable[[str], None],
    snapshot_fn: Callable[[SimulatedEvent], None] | None = None,
    trace_fn: Callable[[bool], Path] | None = None,
    xml_fn: Callable[[], str] | None = None,
) -> None:
    accounting = AccountingEngine()
    set_trace = trace_fn or set_netconf_trace_enabled
    trace_enabled = False
    trace_tailer: NetconfTraceTailer | None = None
    current_event: SimulatedEvent | None = None
    previous_event: SimulatedEvent | None = None
    current_data: dict[str, object] | None = None
    visible_energy_object_ids: frozenset[str] | None = None
    if simulator.use_case is not None:
        scenario = simulator.network.scenarios_by_uc[simulator.use_case.value]
        visible_energy_object_ids = _visible_energy_object_ids_for_use_case(
            simulator, simulator.use_case, scenario.topology_ids
        )
    output_fn("GREEN allrun51 demo starting...")

    def disable_trace() -> None:
        nonlocal trace_enabled, trace_tailer
        if not trace_enabled:
            return
        try:
            trace_path = set_trace(False)
        except OSError as error:
            output_fn(f"NETCONF trace could not be disabled: {error}")
        else:
            output_fn(f"NETCONF trace disabled: {trace_path}")
        trace_enabled = False
        if trace_tailer is not None:
            trace_tailer.stop()
            trace_tailer = None

    def show_view(command: str) -> None:
        if command == "xml":
            try:
                xml = (
                    xml_fn()
                    if xml_fn is not None
                    else fetch_netconf_xml(visible_energy_object_ids)
                )
                output_fn(xml)
            except Exception as error:
                output_fn(f"NETCONF XML view unavailable: {error}")
            return
        if current_event is None or current_data is None:
            output_fn(f"{command} view unavailable before the first event.")
            return
        if command == "summary":
            output_fn(render_summary(
                current_event,
                current_data,
                visible_energy_object_ids=visible_energy_object_ids,
            ))
        elif command == "relationships":
            output_fn(render_relationships(current_data))
        elif command == "json":
            output_fn(render_json(current_data))
        elif command == "diff":
            output_fn(render_relationship_diff(
                previous_event,
                current_event,
                visible_energy_object_ids=visible_energy_object_ids,
            ))

    while simulator.has_next:
        next_spec = simulator.peek_next()
        if next_spec is None:
            break
        next_series = next_spec.series
    # Print a separator at each use-case boundary.
        if current_event is None or current_event.series != next_series:
            output_fn(f"--- {next_series.value} {USE_CASES_BY_SERIES[next_series].title} ---")

        if not auto:
            output_fn("Enter next | a auto | d netconf | summary / relationships / json / xml / diff | r restart | q quit")
            command = input_fn().strip().lower()
            if command == "a":
                auto = True
                output_fn("Automatic mode enabled.")
                continue
            if command == "d":
                next_trace_state = not trace_enabled
                try:
                    trace_path = set_trace(next_trace_state)
                except OSError as error:
                    output_fn(f"NETCONF trace could not be updated: {error}")
                    continue
                trace_enabled = next_trace_state
                if trace_enabled:
                    trace_tailer = NetconfTraceTailer(
                        trace_path,
                        output_fn,
                        visible_energy_object_ids=visible_energy_object_ids,
                    )
                    trace_tailer.start()
                    output_fn(f"NETCONF trace enabled (live view): {trace_path}")
                else:
                    if trace_tailer is not None:
                        trace_tailer.stop()
                        trace_tailer = None
                    output_fn(f"NETCONF trace disabled: {trace_path}")
                continue
            if command == "q":
                disable_trace()
                output_fn("GREEN allrun51 demo stopped.")
                return
            if command == "r":
                simulator.reset()
                current_event = None
                previous_event = None
                current_data = None
                output_fn("All Group A state reset to UC 2.1 / U1-0.")
                continue
            if command in _VIEW_COMMANDS:
                show_view(command)
                continue
            if command:
                output_fn("Unknown command. Choose ENTER, a, d, summary, relationships, json, xml, diff, r, or q.")
                continue

        event = simulator.next_event()
        if event is None:
            break
        visible_energy_object_ids = _visible_energy_object_ids_for_use_case(
            simulator, event.series, event.topology_ids
        )
        if trace_tailer is not None:
            trace_tailer.visible_energy_object_ids = visible_energy_object_ids
        if snapshot_fn is not None:
            try:
                snapshot_fn(event)
            except OSError as error:
                output_fn(f"NETCONF snapshot warning: {error}")

        topology, boundary = build_demo_topology(relationships=event.relationships)
        result = None
        if event.series is EventSeries.UC_2_13:
            result = accounting.compute(
                boundary,
                event.measurements,
                topology,
                series=event.series.value,
                event_sequence=event.sequence,
                event_name=event.name,
            )
        data = event_to_yang(event, simulator.energy_objects)
        if visible_energy_object_ids is not None:
            data = filter_yang_instance_to_energy_objects(data, visible_energy_object_ids)
        prior_event = current_event
        previous_event, current_event = current_event, event
        current_data = data
        _display_event(
            event,
            result,
            topology,
            output_fn,
            prior_event,
            visible_energy_object_ids,
        )

        next_spec = simulator.peek_next()
        if next_spec is None:
            output_fn(f"{event.series.value} complete")
        elif next_spec.series != event.series:
            output_fn(f"{event.series.value} complete -> {next_spec.series.value} {USE_CASES_BY_SERIES[next_spec.series].title}")

        if auto and simulator.has_next:
            sleep_fn(interval)

    disable_trace()
    if simulator.use_case is None:
        output_fn("Group A completed: 14 use cases")
        output_fn("Group B deferred: 2 use cases")
    else:
        output_fn(f"{simulator.use_case.value} completed")


def _display_event(
    event: SimulatedEvent,
    result: AccountingResult | None,
    topology: RelationshipGraph,
    output_fn: Callable[[str], None],
    previous: SimulatedEvent | None,
    visible_energy_object_ids: frozenset[str] | None = None,
) -> None:
    use_color = output_fn is print and sys.stdout.isatty()
    for line in render_compact_event(
        event,
        topology.energy_objects,
        previous,
        result,
        visible_energy_object_ids,
    ).splitlines():
        if use_color and line.startswith("["):
            line = f"\x1b[32m{line}\x1b[0m"
        output_fn(line)


def _visible_energy_object_ids(
    simulator: EventSimulator,
    topology_ids: Sequence[str],
) -> frozenset[str]:
    selected_topologies = set(topology_ids)
    return frozenset(
        energy_object_id
        for topology in simulator.network.topologies
        if topology.topology_id in selected_topologies
        for energy_object_id in topology.energy_object_ids
    )


def _visible_energy_object_ids_for_use_case(
    simulator: EventSimulator,
    series: EventSeries,
    topology_ids: Sequence[str],
) -> frozenset[str]:
    topology_object_ids = _visible_energy_object_ids(simulator, topology_ids)
    use_case_value_ids = {
        energy_object_id
        for event in EVENT_CATALOG
        if event.series is series
        for energy_object_id, _ in (
            *event.interval_energy_wh,
            *event.instantaneous_power_w,
            *event.component_states,
        )
    }
    return frozenset(topology_object_ids & use_case_value_ids)


def main(
    argv: Sequence[str] | None = None,
    *,
    input_fn: Callable[[], str] = input,
    sleep_fn: Callable[[float], None] = time.sleep,
    output_fn: Callable[[str], None] = print,
    snapshot_fn: Callable[[SimulatedEvent], None] | None = write_operational_snapshot,
    trace_fn: Callable[[bool], Path] | None = None,
    xml_fn: Callable[[], str] | None = None,
) -> None:
    parser = argparse.ArgumentParser(description="Run the GREEN allrun51 event simulator")
    parser.add_argument("--auto", action="store_true", help="run all remaining events without prompts")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument(
        "-u",
        "--uc",
        type=parse_use_case,
        metavar="UC",
        help=f"run only one implemented UC (available: {', '.join(SUPPORTED_USE_CASE_IDS)})",
    )
    args = parser.parse_args(argv)
    if args.interval < 0:
        parser.error("--interval must be non-negative")

    set_trace = trace_fn or set_netconf_trace_enabled
    try:
        set_trace(False)
    except OSError as error:
        output_fn(f"NETCONF trace could not be reset: {error}")
    run_demo(
        EventSimulator(use_case=args.uc),
        auto=args.auto,
        interval=args.interval,
        input_fn=input_fn,
        sleep_fn=sleep_fn,
        output_fn=output_fn,
        snapshot_fn=snapshot_fn,
        trace_fn=set_trace,
        xml_fn=xml_fn,
    )


if __name__ == "__main__":
    main()
