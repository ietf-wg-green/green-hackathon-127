from collections import Counter

from green.catalog import UC_CATALOG
from green.models import ComponentState, EventSeries, RelationshipType
from green.simulator import EventSimulator, generate_events
from green.topology import (
    LINECARD_1_ID,
    LINECARD_2_ID,
    NON_CRITICAL_PORT_ID,
    ROUTER_A_ID,
    ROUTER_B_ID,
    SERVER_A_ID,
    SERVER_B_ID,
    UPSTREAM_METER_ID,
    demo_energy_objects,
)


def events_by_sequence():
    return {event.sequence: event for event in generate_events()}


def values_by_object(events, field: str, object_id: str) -> list[int | None]:
    return [
        getattr(next(item for item in event.measurements if item.energy_object_id == object_id), field)
        for event in events
    ]


EXPECTED_EVENT_COUNTS = {
    EventSeries.UC_2_1: 8,
    EventSeries.UC_2_2: 10,
    EventSeries.UC_2_5: 8,
    EventSeries.UC_2_6: 8,
    EventSeries.UC_2_7: 8,
    EventSeries.UC_2_8: 8,
    EventSeries.UC_2_9: 10,
    EventSeries.UC_2_10: 8,
    EventSeries.UC_2_11: 8,
    EventSeries.UC_2_12: 10,
    EventSeries.UC_2_13: 8,
    EventSeries.UC_2_14: 10,
    EventSeries.UC_2_15: 8,
    EventSeries.UC_2_16: 10,
}


def test_catalog_runs_all_group_a_use_cases_in_numeric_order() -> None:
    events = generate_events()
    assert len(UC_CATALOG) == 14
    assert len(events) == 122
    assert Counter(event.series for event in events) == EXPECTED_EVENT_COUNTS
    assert len({event.sequence for event in events}) == 122
    assert [event.sequence for event in events] == [
        spec.sequence for use_case in UC_CATALOG for spec in use_case.events
    ]
    assert [event.series for event in events] == [
        use_case.series for use_case in UC_CATALOG for _ in use_case.events
    ]
    assert [len(use_case.events) for use_case in UC_CATALOG] == [
        EXPECTED_EVENT_COUNTS[use_case.series] for use_case in UC_CATALOG
    ]


def test_selected_use_case_nicknames_survive_event_expansion() -> None:
    nicknames = {use_case.series: use_case.nickname for use_case in UC_CATALOG}

    assert nicknames[EventSeries.UC_2_1] == "Incremental"
    assert nicknames[EventSeries.UC_2_2] == "Proportional"
    assert nicknames[EventSeries.UC_2_5] == "Indirect_meter"
    assert nicknames[EventSeries.UC_2_8] == "Video streaming"
    assert nicknames[EventSeries.UC_2_9] == "WLAN"
    assert nicknames[EventSeries.UC_2_12] == "Smart-City"
    assert nicknames[EventSeries.UC_2_16] == "Cross-Layer"
    assert all(
        len(nickname.replace("_", " ").replace("-", " ").split()) <= 2
        for nickname in (
            nicknames[EventSeries.UC_2_1],
            nicknames[EventSeries.UC_2_2],
            nicknames[EventSeries.UC_2_5],
            nicknames[EventSeries.UC_2_8],
            nicknames[EventSeries.UC_2_9],
            nicknames[EventSeries.UC_2_12],
            nicknames[EventSeries.UC_2_16],
        )
    )


def test_simulator_can_select_one_use_case() -> None:
    events = generate_events(EventSeries.UC_2_13)
    assert len(events) == EXPECTED_EVENT_COUNTS[EventSeries.UC_2_13]
    assert all(event.series is EventSeries.UC_2_13 for event in events)
    assert [event.sequence for event in events] == [f"U13-{index}" for index in range(8)]

    simulator = EventSimulator(use_case=EventSeries.UC_2_13)
    assert simulator.peek_next() is not None
    assert simulator.peek_next().sequence == "U13-0"
    assert len(tuple(iter(lambda: simulator.next_event(), None))) == 8


def test_every_event_has_one_short_deterministic_sentence() -> None:
    events = generate_events()
    assert all(event.explanation.strip() for event in events)
    assert all(len(event.explanation.split()) < 20 for event in events)
    assert all(event.explanation.endswith(".") for event in events)
    assert all(event.explanation.count(".") == 1 for event in events)


def test_existing_uc213_measurements_and_topology_progression_are_preserved() -> None:
    events = [events_by_sequence()[f"U13-{index}"] for index in range(4)]
    assert values_by_object(events, "interval_energy_wh", UPSTREAM_METER_ID) == [300, 300, 340, 310]
    assert values_by_object(events, "interval_energy_wh", SERVER_A_ID) == [120, 120, 140, 125]
    assert values_by_object(events, "interval_energy_wh", SERVER_B_ID) == [180, 180, 190, 175]
    assert [len(event.metering_relationships) for event in events] == [0, 4, 4, 2]
    assert dict(events[0].metadata)["relationship-change"] == "topology-not-discovered"


def test_uc210_router_power_and_linecard_states_are_preserved() -> None:
    events = [events_by_sequence()[f"U10-{index}"] for index in range(4)]
    assert all(not event.measurements for event in events)
    assert [
        {item.energy_object_id: item.instantaneous_power_w for item in event.power_measurements}
        for event in events
    ] == [
        {ROUTER_A_ID: 500, ROUTER_B_ID: 480},
        {ROUTER_A_ID: 340, ROUTER_B_ID: 330},
        {ROUTER_A_ID: 220, ROUTER_B_ID: 390},
        {ROUTER_A_ID: 460, ROUTER_B_ID: 470},
    ]
    assert [dict(event.component_states)[LINECARD_1_ID] for event in events] == [
        ComponentState.ACTIVE,
        ComponentState.ACTIVE,
        ComponentState.LOW_POWER,
        ComponentState.ACTIVE,
    ]


def test_existing_uc21_baseline_and_measurement_values_are_preserved() -> None:
    events = [events_by_sequence()[f"U1-{index}"] for index in range(4)]
    assert events[0].measurements == () and events[0].power_measurements == ()
    assert dict(events[0].metadata)["classification"] == "baseline-only"
    assert {item.energy_object_id for item in events[1].power_measurements} == {LINECARD_1_ID}
    assert dict(events[2].metadata)["observed-power-w"] == "420"
    assert {item.energy_object_id: item.instantaneous_power_w for item in events[3].power_measurements} == {
        ROUTER_A_ID: 420,
        ROUTER_B_ID: 380,
    }
    assert LINECARD_2_ID not in {item.energy_object_id for item in events[1].power_measurements}


def test_existing_uc214_power_shortage_states_and_power_are_preserved() -> None:
    events = [events_by_sequence()[f"U14-{index}"] for index in range(5)]
    assert [dict(event.metadata).get("power-source") for event in events] == [
        "grid", "battery", "battery", "battery", "grid"
    ]
    assert [dict(event.metadata).get("battery-level-percent") for event in events[1:4]] == [
        "100", "55", "15"
    ]
    assert dict(events[2].component_states)[ROUTER_B_ID] is ComponentState.LOW_POWER
    assert dict(events[2].component_states)[NON_CRITICAL_PORT_ID] is ComponentState.OFF
    assert dict(events[3].component_states)[ROUTER_A_ID] is ComponentState.ACTIVE


def test_all_relationship_peers_are_known_and_relationships_are_unique() -> None:
    known = {item.energy_object_id for item in demo_energy_objects()}
    for event in generate_events():
        keys = set()
        for relationship in event.relationships:
            key = (
                relationship.source_energy_object_id,
                relationship.relationship_type,
                relationship.peer_energy_object_id,
            )
            assert relationship.source_energy_object_id != relationship.peer_energy_object_id
            assert relationship.source_energy_object_id in known
            assert relationship.peer_energy_object_id in known
            assert key not in keys
            keys.add(key)
    assert {rel.relationship_type for event in generate_events() for rel in event.relationships} == set(
        RelationshipType
    )


def test_reset_restarts_first_event_and_uc210_power_observation() -> None:
    simulator = EventSimulator()
    events = []
    while (event := simulator.next_event()) is not None:
        events.append(event)
    assert events[-1].sequence == "U16-9"
    simulator.reset()
    assert simulator.next_event().sequence == "U1-0"
    restarted = None
    while (event := simulator.next_event()) is not None:
        if event.sequence == "U10-0":
            restarted = event
            break
    assert restarted is not None
    assert restarted.measurements == ()
    assert {
        item.energy_object_id: item.instantaneous_power_w
        for item in restarted.power_measurements
    } == {ROUTER_A_ID: 500, ROUTER_B_ID: 480}
