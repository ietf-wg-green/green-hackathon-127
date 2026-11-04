import json
from collections import defaultdict

from green.cli import _visible_energy_object_ids_for_use_case, run_demo
from green.simulator import EventSimulator, generate_events


def test_full_stream_json_keeps_use_case_value_bearing_context() -> None:
    commands = iter(["", "", "json", "q"])
    output: list[str] = []
    simulator = EventSimulator()

    run_demo(
        simulator,
        auto=False,
        interval=0,
        input_fn=lambda: next(commands),
        sleep_fn=lambda _: None,
        output_fn=output.append,
        snapshot_fn=None,
    )

    json_output = next(item for item in output if item.startswith("{"))
    data = json.loads(json_output)
    actual_ids = {
        item["id"]
        for item in data["ietf-power-and-energy:energy-objects"]["energy-object"]
    }

    event = EventSimulator().next_event()
    assert event is not None
    scenario = simulator.network.scenarios_by_uc[event.series.value]
    expected_ids = _visible_energy_object_ids_for_use_case(
        simulator, event.series, scenario.topology_ids
    )
    assert actual_ids == expected_ids
    assert "eo-router-a" in actual_ids
    assert "eo-router-b" in actual_ids
    assert "eo-ap-1" not in actual_ids


def test_baseline_only_event_does_not_expose_unmeasured_energy_objects() -> None:
    commands = iter(["", "json", "q"])
    output: list[str] = []

    run_demo(
        EventSimulator(),
        auto=False,
        interval=0,
        input_fn=lambda: next(commands),
        sleep_fn=lambda _: None,
        output_fn=output.append,
        snapshot_fn=None,
    )

    json_output = next(item for item in output if item.startswith("{"))
    data = json.loads(json_output)
    objects = data["ietf-power-and-energy:energy-objects"]["energy-object"]
    assert {item["id"] for item in objects} == {
        "eo-router-a",
        "eo-router-b",
        "eo-router-a-linecard-1",
    }
    assert all(
        not {"power", "power-state", "energy"}.intersection(item)
        for item in objects
    )


def test_every_event_keeps_only_uc_objects_with_explicit_values() -> None:
    simulator = EventSimulator()
    events = generate_events()
    uc_value_ids: dict[str, set[str]] = defaultdict(set)

    for event in events:
        value_ids = uc_value_ids[event.series.value]
        value_ids.update(
            measurement.energy_object_id for measurement in event.measurements
        )
        value_ids.update(
            measurement.energy_object_id for measurement in event.power_measurements
        )
        value_ids.update(object_id for object_id, _ in event.component_states)

    for event in events:
        visible_ids = _visible_energy_object_ids_for_use_case(
            simulator, event.series, event.topology_ids
        )
        assert visible_ids == uc_value_ids[event.series.value], event.sequence
