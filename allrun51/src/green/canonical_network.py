from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from green.catalog import EVENT_CATALOG, relationships_for_profiles
from green.models import EnergyObject, EnergyRelationship, EventSeries, RelationshipType
from green.topology import demo_energy_objects


DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
STABLE_STRUCTURAL = "stable-structural"
PHYSICAL_DYNAMIC = "physical-dynamic"
KNOWLEDGE_OBSERVABILITY = "knowledge-observability"


@dataclass(frozen=True)
class DeviceArchetype:
    archetype_id: str
    name: str
    component_roles: tuple[str, ...]


@dataclass(frozen=True)
class DeviceInstance:
    device_id: str
    name: str
    archetype_id: str


@dataclass(frozen=True)
class TopologySubgraph:
    topology_id: str
    name: str
    device_ids: tuple[str, ...]
    energy_object_ids: tuple[str, ...]
    relationship_profiles: tuple[str, ...]


@dataclass(frozen=True)
class UCScenario:
    uc: str
    primary: tuple[str, ...]
    secondary: tuple[str, ...]

    @property
    def topology_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.primary, *self.secondary)))


@dataclass(frozen=True)
class RelationshipBehavior:
    relationship: EnergyRelationship
    behavior_class: str


@dataclass(frozen=True)
class CanonicalNetwork:
    network_id: str
    archetypes: tuple[DeviceArchetype, ...]
    device_instances: tuple[DeviceInstance, ...]
    topologies: tuple[TopologySubgraph, ...]
    scenarios: tuple[UCScenario, ...]
    energy_objects: tuple[EnergyObject, ...]
    relationship_behaviors: tuple[RelationshipBehavior, ...]

    @property
    def archetypes_by_id(self) -> dict[str, DeviceArchetype]:
        return {item.archetype_id: item for item in self.archetypes}

    @property
    def devices_by_id(self) -> dict[str, DeviceInstance]:
        return {item.device_id: item for item in self.device_instances}

    @property
    def topologies_by_id(self) -> dict[str, TopologySubgraph]:
        return {item.topology_id: item for item in self.topologies}

    @property
    def scenarios_by_uc(self) -> dict[str, UCScenario]:
        return {item.uc: item for item in self.scenarios}

    @property
    def relationships_by_key(self) -> dict[tuple[str, str, str], RelationshipBehavior]:
        return {
            (
                item.relationship.source_energy_object_id,
                item.relationship.relationship_type.value,
                item.relationship.peer_energy_object_id,
            ): item
            for item in self.relationship_behaviors
        }

    @property
    def stable_structural_relationships(self) -> tuple[EnergyRelationship, ...]:
        return tuple(
            item.relationship
            for item in self.relationship_behaviors
            if item.behavior_class == STABLE_STRUCTURAL
        )

    def actual_relationships_for_profiles(
        self,
        profiles: tuple[str, ...],
    ) -> tuple[EnergyRelationship, ...]:
        active = relationships_for_profiles(profiles)
        active_dynamic = {
            (
                item.source_energy_object_id,
                item.relationship_type.value,
                item.peer_energy_object_id,
            )
            for item in active
        }
        selected = []
        for item in self.relationship_behaviors:
            relationship = item.relationship
            key = (
                relationship.source_energy_object_id,
                relationship.relationship_type.value,
                relationship.peer_energy_object_id,
            )
            if item.behavior_class != PHYSICAL_DYNAMIC or key in active_dynamic:
                selected.append(relationship)
        return tuple(selected)


def load_canonical_network() -> CanonicalNetwork:
    archetype_data = _read_json(DATA_ROOT / "devices" / "archetypes.json")
    instance_data = _read_json(DATA_ROOT / "devices" / "instances.json")
    manifest = _read_json(DATA_ROOT / "topologies" / "demo-network.json")
    scenario_data = _read_json(DATA_ROOT / "scenarios" / "uc-topology-matrix.json")
    behavior_data = _read_json(
        DATA_ROOT / "topologies" / "relationship-behavior-classes.json"
    )

    archetypes = tuple(
        DeviceArchetype(
            item["archetype_id"],
            item["name"],
            tuple(item["component_roles"]),
        )
        for item in archetype_data["archetypes"]
    )
    device_instances = tuple(
        DeviceInstance(item["device_id"], item["name"], item["archetype_id"])
        for item in instance_data["device_instances"]
    )
    energy_objects = demo_energy_objects()

    _require_unique((item.archetype_id for item in archetypes), "device archetype")
    _require_unique((item.device_id for item in device_instances), "device instance")
    archetype_ids = {item.archetype_id for item in archetypes}
    devices_by_id = {item.device_id: item for item in device_instances}
    if any(item.archetype_id not in archetype_ids for item in device_instances):
        raise ValueError("a device instance references an unknown archetype")

    object_device_ids = {item.device_id for item in energy_objects}
    if object_device_ids != set(devices_by_id):
        raise ValueError(
            "device instance mapping does not exactly cover the canonical Energy Objects"
        )
    component_keys = [
        (item.device_id, item.hardware_component_name)
        for item in energy_objects
        if item.hardware_component_name is not None
    ]
    object_keys = [(item.device_id, item.energy_object_id) for item in energy_objects]
    component_names = {item.hardware_component_name for item in energy_objects}
    component_uuids = [item.hardware_component_uuid for item in energy_objects]
    _require_unique(component_keys, "controller-scoped Component")
    _require_unique(object_keys, "controller-scoped Energy Object")
    _require_unique((item.energy_object_id for item in energy_objects), "Energy Object")
    _require_unique((value for value in component_uuids if value is not None), "hardware UUID")
    if any(item.hardware_component_name == item.hardware_component_uuid for item in energy_objects):
        raise ValueError("hardware component name and UUID must remain distinct")
    if any(
        item.hardware_parent_name is not None
        and item.hardware_parent_name not in component_names
        for item in energy_objects
    ):
        raise ValueError("hardware parent is not represented in the canonical inventory")

    topologies = _load_topologies(manifest["subtopologies"], devices_by_id, energy_objects)
    topology_ids = {item.topology_id for item in topologies}
    covered_devices = {device_id for item in topologies for device_id in item.device_ids}
    if covered_devices != set(devices_by_id):
        raise ValueError("the six sub-topologies do not cover every device instance")

    scenarios = tuple(
        UCScenario(item["uc"], tuple(item["primary"]), tuple(item["secondary"]))
        for item in scenario_data["scenarios"]
    )
    _require_unique((item.uc for item in scenarios), "UC topology mapping")
    expected_ucs = {item.value for item in EventSeries}
    if {item.uc for item in scenarios} != expected_ucs:
        raise ValueError("UC topology mapping does not cover every Group A use case")
    if any(topology_id not in topology_ids for item in scenarios for topology_id in item.topology_ids):
        raise ValueError("a UC topology mapping references an unknown sub-topology")

    relationship_classes = behavior_data["relationship_type_classes"]
    expected_relationship_types = {item.value for item in RelationshipType}
    if set(relationship_classes) != expected_relationship_types:
        raise ValueError("relationship behavior classes do not cover every GREEN relationship type")

    profiles = tuple(dict.fromkeys(
        profile
        for topology in topologies
        for profile in topology.relationship_profiles
    ))
    event_profiles = {
        profile
        for event in EVENT_CATALOG
        for profile in event.relationship_profiles
    }
    if not event_profiles <= set(profiles):
        raise ValueError("an event relationship profile is not assigned to a canonical topology")
    relationships = relationships_for_profiles(profiles)
    relationship_map: dict[tuple[str, str, str], EnergyRelationship] = {}
    object_ids = {item.energy_object_id for item in energy_objects}
    for relationship in relationships:
        if relationship.source_energy_object_id not in object_ids or relationship.peer_energy_object_id not in object_ids:
            raise ValueError(f"canonical relationship {relationship.relationship_id} references an unknown object")
        key = (
            relationship.source_energy_object_id,
            relationship.relationship_type.value,
            relationship.peer_energy_object_id,
        )
        relationship_map[key] = relationship
    relationship_behaviors = tuple(
        RelationshipBehavior(
            relationship,
            relationship_classes[relationship.relationship_type.value],
        )
        for _, relationship in sorted(relationship_map.items())
    )

    return CanonicalNetwork(
        manifest["network_id"],
        archetypes,
        device_instances,
        topologies,
        scenarios,
        energy_objects,
        relationship_behaviors,
    )


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object in {path}")
    return value


def _load_topologies(
    topology_ids: list[str],
    devices_by_id: dict[str, DeviceInstance],
    energy_objects: tuple[EnergyObject, ...],
) -> tuple[TopologySubgraph, ...]:
    topologies = []
    for topology_id in topology_ids:
        path = _topology_file(topology_id)
        data = _read_json(path)
        device_ids = tuple(data["device_ids"])
        if len(set(device_ids)) != len(device_ids):
            raise ValueError(f"duplicate device ID in {topology_id}")
        if any(device_id not in devices_by_id for device_id in device_ids):
            raise ValueError(f"unknown device ID in {topology_id}")
        object_ids = tuple(
            item.energy_object_id
            for item in energy_objects
            if item.device_id in device_ids
        )
        topologies.append(
            TopologySubgraph(
                data["topology_id"],
                data["name"],
                device_ids,
                object_ids,
                tuple(data["relationship_profiles"]),
            )
        )
    _require_unique((item.topology_id for item in topologies), "topology subgraph")
    if {item.topology_id for item in topologies} != set(topology_ids):
        raise ValueError("demo network manifest does not match topology files")
    return tuple(topologies)


def _topology_file(topology_id: str) -> Path:
    matches = [
        path
        for path in (DATA_ROOT / "topologies").glob("t*.json")
        if _read_json(path).get("topology_id") == topology_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one file for topology {topology_id}")
    return matches[0]


def _require_unique(values, label: str) -> None:
    materialized = tuple(values)
    if len(set(materialized)) != len(materialized):
        raise ValueError(f"duplicate {label} identifier")