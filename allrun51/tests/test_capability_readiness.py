from __future__ import annotations

import json
from pathlib import Path

from green.capability_readiness import CAPABILITY_DEMO_SELECTIONS, readiness_rows, write_readiness_document
from green.catalog import UC_CATALOG
from green.markdown_tables import align_markdown_tables
from green.models import RelationshipType
from green.simulator import EventSimulator
from green.topology import demo_energy_objects
from green.yang_adapter import to_yang_instance


REPOSITORY = Path(__file__).resolve().parents[1]


def test_readiness_document_lists_stable_distinct_hardware_and_energy_ids() -> None:
    destination = write_readiness_document()
    document = destination.read_text(encoding="utf-8")
    rows = readiness_rows()
    assert destination == REPOSITORY / "docs" / "capability_discovery_readiness.md"
    assert len(rows) == len(CAPABILITY_DEMO_SELECTIONS) == 7
    for row in rows:
        assert row["hardware_component_name"]
        assert row["hardware_component_uuid"]
        assert row["device_id"]
        assert row["device_archetype"]
        assert row["topology"]
        assert row["hardware_component_name"] != row["hardware_component_uuid"]
        assert row["energy_object_id"] != row["hardware_component_name"]
        assert row["source_component_id"] == row["hardware_component_name"]
        assert row["future_capability_profile_class"]
        assert row["hardware_component_name"] in document
        assert row["hardware_component_uuid"] in document
        assert row["energy_object_id"] in document
    assert "ietf-power-state-capabilities" in document
    assert "does not implement" in document
    assert "server-nic" in document and "isac-sensing-component" in document
    assert align_markdown_tables(document) == document


def test_selected_mappings_and_relationship_peers_are_stable_across_all_events_and_restart() -> None:
    objects = demo_energy_objects()
    objects_by_id = {item.energy_object_id: item for item in objects}
    selected_rows = readiness_rows()
    selected_by_uc: dict[str, set[str]] = {}
    for row in selected_rows:
        for uc in row["uc"].split(", "):
            selected_by_uc.setdefault(uc, set()).add(row["energy_object_id"])

    simulator = EventSimulator(objects)
    observed_mappings: dict[str, tuple[str, str]] = {}
    relevant_events = 0
    while (event := simulator.next_event()) is not None:
        if event.series.value not in selected_by_uc:
            continue
        relevant_events += 1
        instance = to_yang_instance(
            objects,
            event.relationships,
            event.measurements,
            event.component_states,
            event.power_measurements,
        )
        hardware = {
            component["name"]: component
            for component in instance["ietf-hardware:hardware"]["component"]
        }
        energy_objects = {
            item["id"]: item
            for item in instance["ietf-power-and-energy:energy-objects"]["energy-object"]
        }
        for energy_id in selected_by_uc[event.series.value]:
            model_object = objects_by_id[energy_id]
            energy_entry = energy_objects[energy_id]
            source_component_id = energy_entry["source-component-id"]
            component = hardware[source_component_id]
            mapping = (component["name"], component["uuid"])
            observed_mappings.setdefault(energy_id, mapping)
            assert observed_mappings[energy_id] == mapping
            assert energy_id != component["name"]
            assert energy_id != component["uuid"]
            assert model_object.hardware_component_name == source_component_id

        for relationship in event.relationships:
            if relationship.relationship_type not in {
                RelationshipType.ENABLING,
                RelationshipType.ENABLED_BY,
            }:
                continue
            if (
                relationship.source_energy_object_id in selected_by_uc[event.series.value]
                or relationship.peer_energy_object_id in selected_by_uc[event.series.value]
            ):
                for peer_id in (
                    relationship.source_energy_object_id,
                    relationship.peer_energy_object_id,
                ):
                    assert peer_id in energy_objects
                    peer_component_name = energy_objects[peer_id]["source-component-id"]
                    assert peer_component_name in hardware

        encoded = json.dumps(instance)
        assert "ietf-system-capabilities" not in encoded
        assert "ietf-power-state-capabilities" not in encoded

    assert relevant_events >= 14
    assert observed_mappings.keys() == set().union(*selected_by_uc.values())

    simulator.reset()
    first_after_reset = simulator.next_event()
    assert first_after_reset is not None and first_after_reset.sequence == "U1-0"
    baseline = {
        item.energy_object_id: (item.hardware_component_name, item.hardware_component_uuid)
        for item in objects
        if item.energy_object_id in observed_mappings
    }
    assert baseline == observed_mappings


def test_uc211_capability_classification_stays_simulator_metadata_only() -> None:
    simulator = EventSimulator()
    event = None
    while (next_event := simulator.next_event()) is not None:
        if next_event.sequence == "U11-2":
            event = next_event
            break
    assert event is not None
    metadata = dict(event.metadata)
    assert metadata["router-A-class"] == "optimized"
    assert metadata["router-B-class"] == "legacy"
    assert metadata["unsupported-capability"] == "unknown"
    instance = to_yang_instance(demo_energy_objects(), event.relationships, event.measurements, event.component_states, event.power_measurements)
    serialized = json.dumps(instance)
    assert "router-A-class" not in serialized
    assert "router-B-class" not in serialized
    assert "unsupported-capability" not in serialized
    assert "ietf-system-capabilities" not in serialized
    assert "ietf-power-state-capabilities" not in serialized
