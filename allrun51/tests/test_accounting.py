from dataclasses import FrozenInstanceError, replace

import pytest

from green.accounting import AccountingEngine, MeasurementValidationError
from green.models import EnergyRelationship, RelationshipType, TopologyStatus
from green.simulator import EventSimulator
from green.topology import (
    SERVER_A_ID,
    SERVER_B_ID,
    UPSTREAM_METER_ID,
    build_demo_topology,
    demo_energy_objects,
    demo_metering_relationships,
)


def events_by_sequence():
    simulator = EventSimulator()
    events = {}
    while (event := simulator.next_event()) is not None:
        events[event.sequence] = event
    return events


def account_event(event, relationships=None):
    selected_relationships = (
        event.metering_relationships if relationships is None else relationships
    )
    topology, boundary = build_demo_topology(relationships=selected_relationships)
    return AccountingEngine().compute(
        boundary,
        event.measurements,
        topology,
        series=event.series.value,
        event_sequence=event.sequence,
        event_name=event.name,
    )


def test_u13_0_reports_raw_total_without_sufficient_topology() -> None:
    event = events_by_sequence()["U13-0"]
    result = account_event(event)

    assert result.naive_total_wh == 600
    assert result.accounted_total_wh is None
    assert result.topology_status is TopologyStatus.INCOMPLETE
    assert result.raw_measurements == event.measurements
    assert result.event_sequence == "U13-0"


def test_u13_1_deduplicates_only_through_explicit_metering_relationships() -> None:
    event = events_by_sequence()["U13-1"]
    result = account_event(event)

    assert result.naive_total_wh == 600
    assert result.accounted_total_wh == 300
    assert result.topology_status is TopologyStatus.COMPLETE
    assert result.raw_measurements == event.measurements
    assert {item.measurement.energy_object_id for item in result.excluded_measurements} == {
        SERVER_A_ID,
        SERVER_B_ID,
    }
    assert all("explicit metering topology" in item.reason for item in result.excluded_measurements)
    assert all(item.relationship_path for item in result.excluded_measurements)
    assert {item.energy_object_id for item in result.included_measurements} == {UPSTREAM_METER_ID}


def test_u13_2_uses_topology_even_when_downstream_sum_differs() -> None:
    event = events_by_sequence()["U13-2"]
    values = {item.energy_object_id: item.interval_energy_wh for item in event.measurements}
    result = account_event(event)

    assert values[SERVER_A_ID] + values[SERVER_B_ID] == 330
    assert values[SERVER_A_ID] + values[SERVER_B_ID] != values[UPSTREAM_METER_ID]
    assert result.naive_total_wh == 670
    assert result.accounted_total_wh == 340
    assert result.topology_status is TopologyStatus.COMPLETE
    assert all(item.relationship_path for item in result.excluded_measurements)


def test_u13_3_missing_one_metering_path_has_no_accounted_total() -> None:
    event = events_by_sequence()["U13-3"]
    result = account_event(event)

    assert result.naive_total_wh == 610
    assert result.accounted_total_wh is None
    assert result.topology_status is TopologyStatus.INCOMPLETE
    assert "eo-server-b" in result.warnings[0]
    assert result.raw_measurements == event.measurements


def test_u10_events_are_not_server_meter_accounting_events() -> None:
    events = events_by_sequence()
    fixed_network_events = [events[f"U10-{index}"] for index in range(8)]

    assert all(not event.measurements for event in fixed_network_events)
    assert all(
        {item.energy_object_id for item in event.power_measurements}
        == {"eo-router-a", "eo-router-b"}
        for event in fixed_network_events
    )


def test_metered_by_relationships_traverse_from_meter_to_metered_object() -> None:
    event = events_by_sequence()["U13-1"]
    relationships = (
        EnergyRelationship("metered-a", RelationshipType.METERED_BY, SERVER_A_ID, UPSTREAM_METER_ID, "test"),
        EnergyRelationship("metered-b", RelationshipType.METERED_BY, SERVER_B_ID, UPSTREAM_METER_ID, "test"),
    )

    result = account_event(event, relationships)

    assert result.accounted_total_wh == 300
    assert result.topology_status is TopologyStatus.COMPLETE


def test_aggregation_and_powering_relationships_do_not_deduplicate() -> None:
    event = events_by_sequence()["U13-1"]
    relationships = (
        EnergyRelationship("aggregate-a", RelationshipType.AGGREGATING, UPSTREAM_METER_ID, SERVER_A_ID, "test"),
        EnergyRelationship("power-b", RelationshipType.POWERED_BY, SERVER_B_ID, UPSTREAM_METER_ID, "test"),
    )

    result = account_event(event, relationships)

    assert result.naive_total_wh == 600
    assert result.accounted_total_wh is None
    assert result.topology_status is TopologyStatus.INCOMPLETE


def test_cycle_is_reported_as_invalid_topology_and_prevents_accounting() -> None:
    event = events_by_sequence()["U13-1"]
    relationships = (
        EnergyRelationship("cycle-a", RelationshipType.METERING, UPSTREAM_METER_ID, SERVER_A_ID, "test"),
        EnergyRelationship("cycle-b", RelationshipType.METERING, SERVER_A_ID, UPSTREAM_METER_ID, "test"),
        demo_metering_relationships()[1],
    )

    result = account_event(event, relationships)

    assert result.accounted_total_wh is None
    assert result.topology_status is TopologyStatus.INVALID
    assert any("cycle detected" in error for error in result.errors)


def test_unknown_relationship_peer_is_a_topology_error() -> None:
    event = events_by_sequence()["U13-1"]
    relationship = EnergyRelationship(
        "unknown-peer",
        RelationshipType.METERING,
        UPSTREAM_METER_ID,
        "eo-unknown",
        "test",
    )

    result = account_event(event, (relationship,))

    assert result.accounted_total_wh is None
    assert result.topology_status is TopologyStatus.INVALID
    assert any("unknown peer" in error for error in result.errors)


@pytest.mark.parametrize(
    ("field", "value"),
    (("unit", "kWh"), ("time_step", "U13-9"), ("metric_type", "power")),
)
def test_incompatible_measurements_are_rejected(field: str, value: str) -> None:
    event = events_by_sequence()["U13-1"]
    measurements = list(event.measurements)
    measurements[1] = replace(measurements[1], **{field: value})
    topology, boundary = build_demo_topology(relationships=event.metering_relationships)

    with pytest.raises(MeasurementValidationError):
        AccountingEngine().compute(
            boundary,
            measurements,
            topology,
            series=event.series.value,
            event_sequence=event.sequence,
            event_name=event.name,
        )


def test_energy_object_identity_fields_are_distinct() -> None:
    meter = demo_energy_objects()[0]

    assert meter.device_id == "pdu-1"
    assert meter.energy_object_id == UPSTREAM_METER_ID
    assert meter.hardware_component_name == "upstream-meter"
    assert meter.hardware_component_uuid != meter.energy_object_id
    assert meter.device_id != meter.energy_object_id
    assert meter.hardware_component_name != meter.energy_object_id


def test_raw_measurements_are_immutable() -> None:
    measurement = events_by_sequence()["U13-1"].measurements[0]

    with pytest.raises(FrozenInstanceError):
        measurement.interval_energy_wh = 0