from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from green.capability_readiness import write_readiness_document
from green.catalog import UC_CATALOG
from green.models import RelationshipType, SimulatedEvent
from green.simulator import generate_events


_RELATIONSHIP_FAMILIES = (
    ("metering / metered-by", RelationshipType.METERING, RelationshipType.METERED_BY),
    ("aggregating / aggregated-by", RelationshipType.AGGREGATING, RelationshipType.AGGREGATED_BY),
    ("powering / powered-by", RelationshipType.POWERING, RelationshipType.POWERED_BY),
    ("enabling / enabled-by", RelationshipType.ENABLING, RelationshipType.ENABLED_BY),
)
_REQUIRED_COVERAGE = {
    "metering / metered-by": ("UC 2.5", "UC 2.9", "UC 2.13"),
    "aggregating / aggregated-by": ("UC 2.6", "UC 2.11", "UC 2.12"),
    "powering / powered-by": ("UC 2.5", "UC 2.9", "UC 2.14"),
    "enabling / enabled-by": ("UC 2.9", "UC 2.10", "UC 2.16"),
}


def _cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", "<br>")


def _event_families(event: SimulatedEvent) -> list[str]:
    relationship_types = {item.relationship_type for item in event.relationships}
    families = [
        name
        for name, forward, inverse in _RELATIONSHIP_FAMILIES
        if forward in relationship_types or inverse in relationship_types
    ]
    if dict(event.metadata).get("relationship-change") and "metering / metered-by" not in families:
        families.append("metering / metered-by (topology transition)")
    return families or ["none"]


def _main_state_data(spec, event: SimulatedEvent) -> str:
    values = [f"{name}={state.value}" for name, state in spec.component_states]
    values.extend(
        f"{item.energy_object_id}={item.instantaneous_power_w} W"
        for item in event.power_measurements
    )
    for item in event.measurements:
        value = f"{item.energy_object_id}={item.interval_energy_wh} Wh interval"
        if item.cumulative_energy_wh is not None:
            value += f", {item.cumulative_energy_wh} Wh cumulative"
        values.append(value)
    if values:
        return "; ".join(values)
    return "metadata-only simulator step" if spec.metadata else "no event-local state or measurement change"


def _yang_visible_data(spec, event: SimulatedEvent) -> str:
    values = ["RFC 8348 inventory", "source-component-id"]
    if event.component_states:
        values.append("power-state/oper")
    if event.power_measurements:
        values.append("power/instantaneous-power")
    if any(item.cumulative_energy_wh is not None for item in event.measurements):
        values.append("energy/total-energy-consumed")
    if event.relationships:
        values.append("relationship/type,peer/id")
    return ", ".join(values)


def render_event_catalog() -> str:
    events_by_id = {event.sequence: event for event in generate_events()}
    lines = [
        "# Group A Event Catalog",
        "",
        f"This catalog is generated from `src/green/catalog.py`: {len(UC_CATALOG)} use cases, {len(events_by_id)} deterministic events.",
        "",
        "Event IDs and descriptions are simulator-specific and are not standardized IETF event names.",
        "",
    ]
    for use_case in UC_CATALOG:
        lines.extend([
            f"## {use_case.series.value} - {use_case.title}",
            "",
            "| UC | Event ID | Event name | Relationship families |",
            "| --- | --- | --- | --- |",
        ])
        for spec in use_case.events:
            event = events_by_id[spec.sequence]
            row = (
                use_case.series.value,
                spec.sequence,
                spec.name,
                ", ".join(_event_families(event)),
            )
            lines.append("| " + " | ".join(_cell(value) for value in row) + " |")
        lines.append("")
        for spec in use_case.events:
            event = events_by_id[spec.sequence]
            metadata = "; ".join(f"{key}={value}" for key, value in spec.metadata) or "none"
            lines.extend([
                f"### {spec.sequence} - {spec.name}",
                "",
                f"- Description: {spec.explanation}",
                f"- Main state/data: {_main_state_data(spec, event)}",
                f"- Relationship families: {', '.join(_event_families(event))}",
                f"- YANG-visible data: {_yang_visible_data(spec, event)}",
                f"- Simulator-only metadata: {metadata}",
                "",
            ])
    return "\n".join(lines) + "\n"


def render_relationship_coverage() -> str:
    events_by_series: dict[str, list[SimulatedEvent]] = defaultdict(list)
    for event in generate_events():
        events_by_series[event.series.value].append(event)

    lines = [
        "# Relationship Coverage",
        "",
        "Relationships are stored directionally as YANG `identityref` values. Demonstration pairs include their explicit inverse; no inverse is synthesized by the views.",
        "",
        "| Family | UC | Event IDs |",
        "| --- | --- | --- |",
    ]
    detail_rows = []
    for family, forward, inverse in _RELATIONSHIP_FAMILIES:
        for use_case in _REQUIRED_COVERAGE[family]:
            selected_events = []
            object_ids: set[str] = set()
            for event in events_by_series[use_case]:
                relationships = [
                    item for item in event.relationships
                    if item.relationship_type in {forward, inverse}
                ]
                is_topology_transition = (
                    family == "metering / metered-by"
                    and bool(dict(event.metadata).get("relationship-change"))
                )
                if relationships or is_topology_transition:
                    selected_events.append(event)
                    for item in relationships:
                        object_ids.add(item.source_energy_object_id)
                        object_ids.add(item.peer_energy_object_id)
            lines.append(
                "| {family} | {uc} | {events} |".format(
                    family=family,
                    uc=use_case,
                    events=", ".join(item.sequence for item in selected_events),
                )
            )
            detail_rows.append(
                f"- {family}, {use_case}: forward `{forward.value}`, inverse `{inverse.value}`; Energy Objects: {', '.join(sorted(object_ids)) or 'topology absent in initial event'}."
            )
    lines.extend([
        "",
        "## Energy Object Details",
        "",
        *detail_rows,
        "",
        "## Accounting Semantics",
        "",
        "Only `metering` / `metered-by` create accounting traversal edges. Aggregation, powering, and enabling remain distinct relationships and never imply metering coverage.",
        "",
    ])
    return "\n".join(lines)


def write_catalog_documents(project_root: Path | None = None) -> tuple[Path, Path, Path]:
    root = project_root or Path(__file__).resolve().parents[2]
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    event_catalog = docs / "event_catalog.md"
    relationship_coverage = docs / "relationship_coverage.md"
    readiness = docs / "capability_discovery_readiness.md"
    event_catalog.write_text(render_event_catalog(), encoding="utf-8")
    relationship_coverage.write_text(render_relationship_coverage(), encoding="utf-8")
    write_readiness_document(readiness)
    return event_catalog, relationship_coverage, readiness


def main() -> None:
    from green.canonical_docs import write_canonical_documents

    for path in write_catalog_documents():
        print(path.relative_to(Path(__file__).resolve().parents[2]))
    for path in write_canonical_documents():
        print(path.relative_to(Path(__file__).resolve().parents[2]))


if __name__ == "__main__":
    main()