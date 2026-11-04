from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from green.catalog import EVENT_CATALOG, UC_CATALOG, relationships_for_profiles
from green.models import RelationshipType
from green.simulator import generate_events
from green.topology import demo_energy_objects
from green.yang_adapter import to_yang_instance


COVERAGE = {
    "metering / metered-by": (
        RelationshipType.METERING,
        RelationshipType.METERED_BY,
        ("UC 2.5", "UC 2.9", "UC 2.13"),
    ),
    "aggregating / aggregated-by": (
        RelationshipType.AGGREGATING,
        RelationshipType.AGGREGATED_BY,
        ("UC 2.6", "UC 2.11", "UC 2.12"),
    ),
    "powering / powered-by": (
        RelationshipType.POWERING,
        RelationshipType.POWERED_BY,
        ("UC 2.5", "UC 2.9", "UC 2.14"),
    ),
    "enabling / enabled-by": (
        RelationshipType.ENABLING,
        RelationshipType.ENABLED_BY,
        ("UC 2.9", "UC 2.10", "UC 2.16"),
    ),
}


def _pipe(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _event_state(event) -> str:
    values = []
    for object_id, state in event.component_states:
        obj = next((item for item in demo_energy_objects() if item.energy_object_id == object_id), None)
        values.append(f"{obj.hardware_component_name if obj else object_id}={state.value}")
    for measurement in event.measurements:
        values.append(f"{measurement.energy_object_id}={measurement.interval_energy_wh} Wh interval")
    for measurement in event.power_measurements:
        values.append(f"{measurement.energy_object_id}={measurement.instantaneous_power_w} W")
    if event.metadata:
        values.extend(f"metadata:{key}={value}" for key, value in event.metadata)
    return "; ".join(values) if values else "No measurement or state asserted; missing data remains unknown"


def _event_relationships(event) -> str:
    families = sorted({
        "metering" if rel.relationship_type in (RelationshipType.METERING, RelationshipType.METERED_BY)
        else "aggregation" if rel.relationship_type in (RelationshipType.AGGREGATING, RelationshipType.AGGREGATED_BY)
        else "powering" if rel.relationship_type in (RelationshipType.POWERING, RelationshipType.POWERED_BY)
        else "enabling"
        for rel in event.relationships
    })
    return ", ".join(families) if families else "none"


def generate_event_catalog() -> str:
    event_by_sequence = {event.sequence: event for event in generate_events()}
    rows = [
        "# Group A Event Catalog",
        "",
        f"This catalog is generated from `src/green/catalog.py`: {len(UC_CATALOG)} use cases, {len(EVENT_CATALOG)} deterministic events.",
        "",
        "| UC | Title | Event ID | Event name | Description | Main state/data | Relationship families | YANG-visible data | Simulator-only metadata |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for spec in EVENT_CATALOG:
        event = event_by_sequence[spec.sequence]
        use_case = next(item for item in UC_CATALOG if item.series is spec.series)
        data = to_yang_instance(
            demo_energy_objects(), event.relationships, event.measurements,
            event.component_states, event.power_measurements,
        )
        yang_objects = data["ietf-power-and-energy:energy-objects"]["energy-object"]
        visible_leaves = sorted({
            leaf
            for item in yang_objects
            for container in ("energy", "power", "power-state")
            if isinstance(item.get(container), dict)
            for leaf in item[container]
        })
        visible = ", ".join(["RFC 8348 inventory", "source-component-id", *visible_leaves])
        metadata_keys = ", ".join(key for key, _ in event.metadata) or "none"
        rows.append(
            "| " + " | ".join(map(_pipe, (
                spec.series.value,
                use_case.title,
                spec.sequence,
                spec.name,
                spec.explanation,
                _event_state(event),
                _event_relationships(event),
                visible,
                metadata_keys,
            ))) + " |"
        )
    return "\n".join(rows) + "\n"


def generate_relationship_coverage() -> str:
    all_events = generate_events()
    rows = [
        "# Relationship Coverage",
        "",
        "Relationships are stored directionally as YANG `identityref` values. Demonstration pairs include their explicit inverse; no inverse is synthesized by the views.",
        "",
        "| Family | UC | Event IDs | Forward identity | Inverse identity | Energy Objects involved |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for family, (forward, inverse, use_cases) in COVERAGE.items():
        for use_case in use_cases:
            selected = [event for event in all_events if event.series.value == use_case]
            event_ids = ", ".join(event.sequence for event in selected)
            relationships = {
                (rel.source_energy_object_id, rel.relationship_type, rel.peer_energy_object_id)
                for event in selected
                for rel in event.relationships
                if rel.relationship_type in (forward, inverse)
            }
            objects = sorted({object_id for source, _, peer in relationships for object_id in (source, peer)})
            rows.append(
                "| " + " | ".join(map(_pipe, (
                    family,
                    use_case,
                    event_ids,
                    forward.value,
                    inverse.value,
                    ", ".join(objects),
                ))) + " |"
            )
    rows.extend((
        "",
        "## Accounting Semantics",
        "",
        "Only `metering` / `metered-by` create accounting traversal edges. Aggregation, powering, and enabling remain distinct relationships and never imply metering coverage.",
    ))
    return "\n".join(rows) + "\n"


def main() -> None:
    from green.catalog_docs import write_catalog_documents
    from green.canonical_docs import write_canonical_documents

    paths = (*write_catalog_documents(PROJECT_ROOT), *write_canonical_documents(PROJECT_ROOT))
    for path in paths:
        print(path.relative_to(PROJECT_ROOT))


if __name__ == "__main__":
    main()
