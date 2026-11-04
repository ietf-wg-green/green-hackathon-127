import json
from dataclasses import replace
from pathlib import Path

from green.accounting import AccountingEngine
from green.models import ComponentState
from green.simulator import EventSimulator
from green.topology import (
    SERVER_A_ID,
    SERVER_B_ID,
    build_demo_topology,
    demo_energy_objects,
    demo_metering_relationships,
)
from green.yang_adapter import from_yang_instance, to_yang_instance


def get_event(sequence: str):
    simulator = EventSimulator()
    while (event := simulator.next_event()) is not None:
        if event.sequence == sequence:
            return event
    raise AssertionError(f"missing simulator event: {sequence}")


def test_energy_objects_map_to_actual_green_and_rfc8348_nodes() -> None:
    objects = demo_energy_objects()
    event = get_event("U13-1")

    instance = to_yang_instance(
        objects,
        event.relationships,
        event.measurements,
        event.component_states,
    )

    hardware_components = instance["ietf-hardware:hardware"]["component"]
    assert {
        "upstream-meter",
        "server-A",
        "server-B",
        "router-A",
        "router-B",
        "linecard-1",
        "linecard-2",
        "switchable-port",
    } <= {component["name"] for component in hardware_components}
    assert all(component["class"] == "iana-hardware:energy-object" for component in hardware_components)

    yang_objects = instance["ietf-power-and-energy:energy-objects"]["energy-object"]
    by_id = {item["id"]: item for item in yang_objects}
    assert by_id["eo-upstream-meter"]["source-component-id"] == "upstream-meter"
    assert by_id["eo-upstream-meter"]["source-component-id"] != objects[0].hardware_component_uuid
    assert by_id["eo-upstream-meter"]["relationship"][0]["peer"] == [
        {"id": "eo-server-a", "details": "allrun51:uc13-full"},
        {"id": "eo-server-b", "details": "allrun51:uc13-full"},
    ]
    assert "energy" not in by_id["eo-server-a"]


def test_metering_relationship_maps_to_schema_identity_and_local_peer_ids() -> None:
    instance = to_yang_instance(demo_energy_objects(), demo_metering_relationships())
    yang_objects = instance["ietf-power-and-energy:energy-objects"]["energy-object"]
    upstream = next(item for item in yang_objects if item["id"] == "eo-upstream-meter")

    assert upstream["relationship"] == [
        {
            "type": "ietf-power-and-energy:metering",
            "peer": [
                {"id": "eo-server-a", "details": "explicit-demo-topology"},
                {"id": "eo-server-b", "details": "explicit-demo-topology"},
            ],
        }
    ]


def test_round_trip_preserves_python_ids_hardware_correlation_and_relationships() -> None:
    objects = demo_energy_objects()
    relationships = demo_metering_relationships()
    instance = to_yang_instance(objects, relationships)

    decoded_objects, decoded_relationships = from_yang_instance(
        instance,
        device_id="unknown-device",
        device_ids_by_energy_object={
            item.energy_object_id: item.device_id for item in objects
        },
    )

    assert decoded_objects == objects
    assert {
        (
            relationship.relationship_type,
            relationship.source_energy_object_id,
            relationship.peer_energy_object_id,
            relationship.provenance,
        )
        for relationship in decoded_relationships
    } == {
        (
            relationship.relationship_type,
            relationship.source_energy_object_id,
            relationship.peer_energy_object_id,
            relationship.provenance,
        )
        for relationship in relationships
    }


def test_traffic_low_maps_router_power_without_server_meter_data() -> None:
    objects = demo_energy_objects()
    event = get_event("U10-1")

    instance = to_yang_instance(
        objects,
        event.relationships,
        event.measurements,
        event.component_states,
        event.power_measurements,
    )
    yang_objects = instance["ietf-power-and-energy:energy-objects"]["energy-object"]
    by_id = {item["id"]: item for item in yang_objects}

    assert by_id["eo-router-a"]["power"]["instantaneous-power"] == "340000"
    assert by_id["eo-router-b"]["power"]["instantaneous-power"] == "330000"
    assert "energy" not in by_id["eo-server-a"]
    assert "energy" not in by_id["eo-upstream-meter"]
    assert "relationship" not in by_id["eo-upstream-meter"]


def test_64_bit_power_values_use_rfc7951_json_strings() -> None:
    event = get_event("U1-1")
    instance = to_yang_instance(
        demo_energy_objects(),
        event.metering_relationships,
        event.measurements,
        event.component_states,
        event.power_measurements,
    )
    by_id = {
        item["id"]: item
        for item in instance["ietf-power-and-energy:energy-objects"]["energy-object"]
    }

    assert by_id["eo-router-a-linecard-1"]["power"]["instantaneous-power"] == "120000"
    assert isinstance(by_id["eo-router-a-linecard-1"]["power"]["instantaneous-power"], str)


def test_yang_mapping_does_not_change_uc_2_13_accounting() -> None:
    event = get_event("U13-1")
    topology, boundary = build_demo_topology(relationships=event.metering_relationships)
    result = AccountingEngine().compute(
        boundary,
        event.measurements,
        topology,
        series=event.series.value,
        event_sequence=event.sequence,
        event_name=event.name,
    )

    to_yang_instance(demo_energy_objects(), event.metering_relationships, event.measurements)

    assert (result.naive_total_wh, result.accounted_total_wh) == (600, 300)


def test_representative_json_examples_match_adapter_output() -> None:
    examples = Path(__file__).parents[1] / "examples"
    hardware_data = json.loads((examples / "hardware-instance.json").read_text())
    energy_data = json.loads((examples / "pdu-instance.json").read_text())

    event = get_event("U13-2")
    example_objects = energy_data["ietf-power-and-energy:energy-objects"]["energy-object"]
    cumulative_by_id = {
        item["id"]: int(item["energy"]["total-energy-consumed"])
        for item in example_objects
        if "energy" in item
    }
    measurements = tuple(
        replace(
            measurement,
            cumulative_energy_wh=cumulative_by_id[measurement.energy_object_id],
        )
        for measurement in event.measurements
    )
    generated_data = to_yang_instance(
        demo_energy_objects(),
        demo_metering_relationships(),
        measurements,
        ((SERVER_A_ID, ComponentState.ACTIVE), (SERVER_B_ID, ComponentState.ACTIVE)),
    )

    example_components = hardware_data["ietf-hardware:hardware"]["component"]
    example_component_names = {component["name"] for component in example_components}
    generated_components = generated_data["ietf-hardware:hardware"]["component"]
    assert [
        {key: value for key, value in component.items() if key != "parent"}
        for component in generated_components
        if component["name"] in example_component_names
    ] == example_components

    example_object_ids = {item["id"] for item in example_objects}
    generated_objects = generated_data["ietf-power-and-energy:energy-objects"]["energy-object"]
    assert [item for item in generated_objects if item["id"] in example_object_ids] == example_objects