from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from green.catalog import EVENT_CATALOG, relationships_for_profiles
from green.models import EnergyObject
from green.topology import demo_energy_objects


class ObservabilityClass(str, Enum):
    FULL = "FULL"
    POWER_ONLY = "POWER_ONLY"
    STATE_ONLY = "STATE_ONLY"
    TOPOLOGY_ONLY = "TOPOLOGY_ONLY"
    UNOBSERVED = "UNOBSERVED"


@dataclass(frozen=True)
class EnergyObjectObservability:
    energy_object_id: str
    device_id: str
    hardware_component_name: str
    observability_class: ObservabilityClass
    power_observed: bool
    state_observed: bool
    energy_observed: bool
    relationships_defined: bool

    def display_power(self, current_value: object | None) -> str:
        if current_value is not None:
            return str(current_value)
        if self.observability_class in {
            ObservabilityClass.FULL,
            ObservabilityClass.POWER_ONLY,
            ObservabilityClass.UNOBSERVED,
        }:
            return "UNKNOWN"
        return "N/A"

    def display_state(self, current_value: object | None) -> str:
        if current_value is not None:
            return str(current_value)
        if self.observability_class in {
            ObservabilityClass.FULL,
            ObservabilityClass.STATE_ONLY,
            ObservabilityClass.UNOBSERVED,
        }:
            return "UNKNOWN"
        return "N/A"

    def display_relationships(self, current_value: str | None) -> str:
        if current_value is not None:
            return current_value
        if self.relationships_defined or self.observability_class is ObservabilityClass.UNOBSERVED:
            return "UNKNOWN"
        return "N/A"


def build_observability_registry(
    energy_objects: tuple[EnergyObject, ...] | None = None,
) -> dict[str, EnergyObjectObservability]:
    objects = energy_objects or demo_energy_objects()
    evidence = {
        item.energy_object_id: {
            "power": False,
            "state": False,
            "energy": False,
            "relationships": False,
        }
        for item in objects
    }
    for event in EVENT_CATALOG:
        for object_id, _ in event.instantaneous_power_w:
            evidence[object_id]["power"] = True
        for object_id, _ in event.component_states:
            evidence[object_id]["state"] = True
        for object_id, _ in event.interval_energy_wh:
            evidence[object_id]["energy"] = True
        for relationship in relationships_for_profiles(event.relationship_profiles):
            evidence[relationship.source_energy_object_id]["relationships"] = True
            evidence[relationship.peer_energy_object_id]["relationships"] = True

    registry = {}
    for item in objects:
        observed = evidence[item.energy_object_id]
        if observed["power"] and observed["state"]:
            classification = ObservabilityClass.FULL
        elif observed["power"]:
            classification = ObservabilityClass.POWER_ONLY
        elif observed["state"]:
            classification = ObservabilityClass.STATE_ONLY
        elif observed["energy"] or observed["relationships"]:
            classification = ObservabilityClass.TOPOLOGY_ONLY
        else:
            classification = ObservabilityClass.UNOBSERVED
        registry[item.energy_object_id] = EnergyObjectObservability(
            item.energy_object_id,
            item.device_id,
            item.hardware_component_name or "",
            classification,
            observed["power"],
            observed["state"],
            observed["energy"],
            observed["relationships"],
        )
    return registry


def render_observability_document(
    energy_objects: tuple[EnergyObject, ...] | None = None,
) -> str:
    objects = energy_objects or demo_energy_objects()
    registry = build_observability_registry(objects)
    lines = [
        "# Energy Object Observability",
        "",
        "Classes describe evidence in the deterministic event catalog, not new YANG leaves. Display-only `UNKNOWN` means applicable but absent from the current observation; `N/A` means the observability profile intentionally does not apply the field. Numeric zero remains the measured value `0`.",
        "",
        "| Energy Object | Class | Power | State | Energy | Relationships |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in objects:
        record = registry[item.energy_object_id]
        lines.append(
            f"| `{record.energy_object_id}` | `{record.observability_class.value}` | {'yes' if record.power_observed else 'no'} | {'yes' if record.state_observed else 'no'} | {'yes' if record.energy_observed else 'no'} | {'yes' if record.relationships_defined else 'no'} |"
        )
    lines.extend(["", "## Object Details", ""])
    for item in objects:
        record = registry[item.energy_object_id]
        lines.extend([
            f"### {record.energy_object_id}",
            "",
            f"- Device ID: `{record.device_id}`",
            f"- Hardware component: `{record.hardware_component_name}`",
            f"- Class: `{record.observability_class.value}`",
            f"- Power evidence: {'observed' if record.power_observed else 'not observed'}",
            f"- State evidence: {'observed' if record.state_observed else 'not observed'}",
            f"- Energy evidence: {'observed' if record.energy_observed else 'not observed'}",
            f"- Relationship evidence: {'defined' if record.relationships_defined else 'not defined'}",
            "",
        ])
    counts = {classification: 0 for classification in ObservabilityClass}
    for record in registry.values():
        counts[record.observability_class] += 1
    lines.extend([
        "",
        "Class semantics: `FULL` has event evidence of both instantaneous Power and power State; `POWER_ONLY` has Power evidence; `STATE_ONLY` has State evidence; `TOPOLOGY_ONLY` has interval/cumulative Energy or relationship evidence but no Power/State evidence; `UNOBSERVED` has no event measurement, state, or relationship evidence beyond inventory identity.",
        "",
        "Counts: " + ", ".join(f"{key.value}={value}" for key, value in counts.items()),
        "",
    ])
    return "\n".join(lines)


def write_observability_document(destination: Path | None = None) -> Path:
    target = destination or Path(__file__).resolve().parents[2] / "docs" / "energy_object_observability.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_observability_document(), encoding="utf-8")
    return target