from pathlib import Path

from green.canonical_network import (
    KNOWLEDGE_OBSERVABILITY,
    PHYSICAL_DYNAMIC,
    STABLE_STRUCTURAL,
    load_canonical_network,
)
from green.controller_identity import ComponentIdentity, EnergyObjectIdentity
from green.models import EventSeries, RelationshipType
from green.netconf_bridge import write_operational_snapshot
from green.simulator import EventSimulator
from green.topology import BACKUP_BATTERY_ID, GRID_SOURCE_ID


def test_canonical_network_loads_all_archetypes_devices_topologies_and_use_cases() -> None:
    network = load_canonical_network()

    assert network.network_id == "DEMO-NETWORK-1"
    assert len(network.archetypes) == 7
    assert len(network.device_instances) == 23
    assert len(network.energy_objects) == 44
    assert "eo-ai-node-1-nic-1" in {item.energy_object_id for item in network.energy_objects}
    assert len(network.topologies) == 6
    assert len(network.scenarios) == 14
    component_keys = {
        ComponentIdentity(item.device_id, item.hardware_component_name)
        for item in network.energy_objects
    }
    energy_object_keys = {
        EnergyObjectIdentity(item.device_id, item.energy_object_id)
        for item in network.energy_objects
    }
    assert len(component_keys) == len(network.energy_objects)
    assert len(energy_object_keys) == len(network.energy_objects)
    assert set(network.scenarios_by_uc) == {
        "UC 2.1", "UC 2.2", "UC 2.5", "UC 2.6", "UC 2.7", "UC 2.8", "UC 2.9",
        "UC 2.10", "UC 2.11", "UC 2.12", "UC 2.13", "UC 2.14", "UC 2.15", "UC 2.16",
    }
    assert {
        item.device_id for topology in network.topologies for item in network.energy_objects
        if item.device_id in topology.device_ids
    } == set(network.devices_by_id)


def test_relationship_inventory_has_explicit_behavior_class_for_every_family() -> None:
    network = load_canonical_network()
    classes = {item.behavior_class for item in network.relationship_behaviors}

    assert classes == {STABLE_STRUCTURAL, PHYSICAL_DYNAMIC, KNOWLEDGE_OBSERVABILITY}
    assert len(network.relationship_behaviors) == 44
    assert network.stable_structural_relationships


def test_controller_identity_scopes_local_names_by_device() -> None:
    first_component = ComponentIdentity("router-A", "linecard-1")
    second_component = ComponentIdentity("router-B", "linecard-1")
    first_energy_object = EnergyObjectIdentity("router-A", "eo-linecard")
    second_energy_object = EnergyObjectIdentity("router-B", "eo-linecard")

    assert first_component != second_component
    assert first_energy_object != second_energy_object


def test_event_patches_keep_inventory_and_structural_relationships_stable() -> None:
    simulator = EventSimulator()
    canonical_objects = tuple(
        (item.device_id, item.hardware_component_name, item.hardware_component_uuid,
         item.energy_object_id, item.hardware_parent_name)
        for item in simulator.energy_objects
    )
    expected_structural = {
        (
            item.source_energy_object_id,
            item.relationship_type,
            item.peer_energy_object_id,
        )
        for item in simulator.network.stable_structural_relationships
    }

    while (event := simulator.next_event()) is not None:
        current_objects = tuple(
            (item.device_id, item.hardware_component_name, item.hardware_component_uuid,
             item.energy_object_id, item.hardware_parent_name)
            for item in simulator.energy_objects
        )
        assert current_objects == canonical_objects
        assert event.topology_ids == simulator.network.scenarios_by_uc[event.series.value].topology_ids
        assert {
            (
                item.source_energy_object_id,
                item.relationship_type,
                item.peer_energy_object_id,
            )
            for item in event.visible_structural_relationships
        } == expected_structural

    simulator.reset()
    restarted_objects = tuple(
        (item.device_id, item.hardware_component_name, item.hardware_component_uuid,
         item.energy_object_id, item.hardware_parent_name)
        for item in simulator.energy_objects
    )
    assert restarted_objects == canonical_objects


def test_each_uc_overlay_starts_from_the_canonical_base_state() -> None:
    simulator = EventSimulator()
    first_uc5 = None
    while (event := simulator.next_event()) is not None:
        if event.sequence == "U5-0":
            first_uc5 = event
            break

    assert first_uc5 is not None
    assert first_uc5.component_states == ()


def test_uc213_actual_metering_topology_is_separate_from_controller_knowledge() -> None:
    events = EventSimulator()
    u13_events = []
    while (event := events.next_event()) is not None:
        if event.series is EventSeries.UC_2_13:
            u13_events.append(event)

    def metering_links(relationships):
        return {
            (item.source_energy_object_id, item.peer_energy_object_id)
            for item in relationships
            if item.relationship_type is RelationshipType.METERING
        }

    assert metering_links(u13_events[0].actual_relationships)
    assert not metering_links(u13_events[0].relationships)
    assert metering_links(u13_events[1].relationships) <= metering_links(u13_events[1].actual_relationships)


def test_uc214_actual_power_relationship_changes_with_active_source() -> None:
    simulator = EventSimulator()
    events = {}
    while (event := simulator.next_event()) is not None:
        if event.sequence in {"U14-0", "U14-1", "U14-8"}:
            events[event.sequence] = event

    def active_sources(sequence: str) -> set[str]:
        return {
            relationship.source_energy_object_id
            for relationship in events[sequence].actual_relationships
            if relationship.relationship_type is RelationshipType.POWERING
            and relationship.peer_energy_object_id in {"eo-router-a", "eo-router-b"}
        }

    assert active_sources("U14-0") == {GRID_SOURCE_ID}
    assert active_sources("U14-1") == {BACKUP_BATTERY_ID}
    assert active_sources("U14-8") == {GRID_SOURCE_ID}


def test_netconf_snapshot_exposes_stable_structure_but_not_undiscovered_metering(tmp_path) -> None:
    simulator = EventSimulator()
    event = None
    while (candidate := simulator.next_event()) is not None:
        if candidate.sequence == "U13-0":
            event = candidate
            break
    assert event is not None

    snapshot_path = write_operational_snapshot(event, tmp_path / "operational.json")
    import json

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    objects = snapshot["ietf-power-and-energy:energy-objects"]["energy-object"]
    relationships = {
        (item["id"], relation["type"], peer["id"])
        for item in objects
        for relation in item.get("relationship", [])
        for peer in relation["peer"]
    }
    assert ("eo-switch-fabric", "ietf-power-and-energy:enabling", "eo-router-a-linecard-1") in relationships
    assert not any(kind == "ietf-power-and-energy:metering" and source == "eo-upstream-meter" for source, kind, _ in relationships)


def test_loader_rejects_controller_component_identity_collisions(monkeypatch) -> None:
    from dataclasses import replace

    import green.canonical_network as canonical_network

    original_objects = canonical_network.demo_energy_objects()
    monkeypatch.setattr(
        canonical_network,
        "demo_energy_objects",
        lambda: (*original_objects, replace(original_objects[0])),
    )

    try:
        canonical_network.load_canonical_network()
    except ValueError as error:
        assert "controller-scoped Component" in str(error)
    else:
        raise AssertionError("duplicate controller-scoped Component key must be rejected")