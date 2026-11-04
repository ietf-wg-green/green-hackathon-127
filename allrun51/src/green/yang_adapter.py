from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from green.models import (
    ComponentState,
    EnergyObject,
    EnergyRelationship,
    MetricType,
    RawPowerMeasurement,
    RawEnergyMeasurement,
    RelationshipType,
)


GREEN_MODULE = "ietf-power-and-energy"
HARDWARE_MODULE = "ietf-hardware"
IANA_HARDWARE_MODULE = "iana-hardware"

_RELATION_TO_IDENTITY = {
    relationship_type: f"{GREEN_MODULE}:{relationship_type.value}"
    for relationship_type in RelationshipType
}
_IDENTITY_TO_RELATION = {
    identity: relationship_type
    for relationship_type, identity in _RELATION_TO_IDENTITY.items()
}
_STATE_TO_IDENTITY = {
    ComponentState.ACTIVE: f"{GREEN_MODULE}:power-state-on",
    ComponentState.LOW_POWER: f"{GREEN_MODULE}:power-state-sleep",
    ComponentState.OFF: f"{GREEN_MODULE}:power-state-off",
}
_IDENTITY_TO_STATE = {identity: state for state, identity in _STATE_TO_IDENTITY.items()}


def to_yang_instance(
    energy_objects: Sequence[EnergyObject],
    relationships: Sequence[EnergyRelationship],
    measurements: Sequence[RawEnergyMeasurement] = (),
    component_states: Sequence[tuple[str, ComponentState]] = (),
    power_measurements: Sequence[RawPowerMeasurement] = (),
) -> dict[str, object]:
    """Convert internal GREEN objects to RFC 7951-shaped hardware/energy data.

    The GREEN schema declares total-energy-consumed in Watt-hours while its
    description says milliwatt-hours. This adapter follows the declared units
    and preserves the internal Wh integer unchanged; it does not scale values.
    """
    objects_by_id = {obj.energy_object_id: obj for obj in energy_objects}
    if len(objects_by_id) != len(energy_objects):
        raise ValueError("duplicate Energy Object IDs")

    components: list[dict[str, object]] = []
    component_names: set[str] = set()
    component_uuids: set[str] = set()
    for energy_object in energy_objects:
        name = energy_object.hardware_component_name
        if not name:
            raise ValueError(
                f"Energy Object {energy_object.energy_object_id} has no hardware component name"
            )
        if name in component_names:
            raise ValueError(f"duplicate hardware component name: {name}")
        component_names.add(name)
        component: dict[str, object] = {
            "name": name,
            "class": f"{IANA_HARDWARE_MODULE}:energy-object",
        }
        if energy_object.hardware_parent_name:
            if energy_object.hardware_parent_name not in component_names and not any(
                existing.hardware_component_name == energy_object.hardware_parent_name
                for existing in energy_objects
            ):
                raise ValueError(
                    f"hardware parent is not represented: {energy_object.hardware_parent_name}"
                )
            component["parent"] = energy_object.hardware_parent_name
        hardware_uuid = energy_object.hardware_component_uuid
        if hardware_uuid:
            if hardware_uuid in component_uuids:
                raise ValueError(f"duplicate hardware component UUID: {hardware_uuid}")
            component_uuids.add(hardware_uuid)
            component["uuid"] = hardware_uuid
        components.append(component)

    measurements_by_object: dict[str, RawEnergyMeasurement] = {}
    for measurement in measurements:
        if measurement.energy_object_id not in objects_by_id:
            raise ValueError(
                f"measurement references unknown Energy Object: {measurement.energy_object_id}"
            )
        if measurement.energy_object_id in measurements_by_object:
            raise ValueError(
                f"duplicate measurement for {measurement.energy_object_id}"
            )
        if measurement.metric_type is not MetricType.ENERGY_CONSUMED:
            raise ValueError("only consumed-energy measurements map to this YANG leaf")
        if measurement.unit != "Wh":
            raise ValueError(f"expected internal Wh, received {measurement.unit}")
        measurements_by_object[measurement.energy_object_id] = measurement

    power_by_object: dict[str, RawPowerMeasurement] = {}
    for measurement in power_measurements:
        if measurement.energy_object_id not in objects_by_id:
            raise ValueError(
                f"power measurement references unknown Energy Object: {measurement.energy_object_id}"
            )
        if measurement.energy_object_id in power_by_object:
            raise ValueError(
                f"duplicate power measurement for {measurement.energy_object_id}"
            )
        power_by_object[measurement.energy_object_id] = measurement

    states_by_object = dict(component_states)
    relationships_by_object: dict[str, dict[RelationshipType, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    seen_relationships: set[tuple[str, RelationshipType, str]] = set()
    for relationship in relationships:
        if relationship.source_energy_object_id == relationship.peer_energy_object_id:
            raise ValueError("Energy Object relationships cannot refer to themselves")
        if relationship.source_energy_object_id not in objects_by_id:
            raise ValueError(
                f"relationship references unknown source: {relationship.source_energy_object_id}"
            )
        if relationship.peer_energy_object_id not in objects_by_id:
            raise ValueError(
                f"relationship references unknown peer: {relationship.peer_energy_object_id}"
            )
        relationship_key = (
            relationship.source_energy_object_id,
            relationship.relationship_type,
            relationship.peer_energy_object_id,
        )
        if relationship_key in seen_relationships:
            raise ValueError(f"duplicate Energy Object relationship: {relationship_key}")
        seen_relationships.add(relationship_key)
        peers = relationships_by_object[relationship.source_energy_object_id][
            relationship.relationship_type
        ]
        peers.append(
            {
                "id": relationship.peer_energy_object_id,
                "details": relationship.provenance,
            }
        )

    yang_energy_objects: list[dict[str, object]] = []
    for energy_object in energy_objects:
        item: dict[str, object] = {"id": energy_object.energy_object_id}
        if energy_object.hardware_component_name:
            item["source-component-id"] = energy_object.hardware_component_name

        measurement = measurements_by_object.get(energy_object.energy_object_id)
        if measurement and measurement.cumulative_energy_wh is not None:
            if measurement.cumulative_energy_wh < 0:
                raise ValueError("cumulative consumed energy cannot be negative")
            item["energy"] = {
                "total-energy-consumed": str(measurement.cumulative_energy_wh),
            }

        power_measurement = power_by_object.get(energy_object.energy_object_id)
        if power_measurement is not None:
            item["power"] = {
                "instantaneous-power": str(power_measurement.instantaneous_power_w * 1000),
            }

        state = states_by_object.get(energy_object.energy_object_id)
        state_identity = _STATE_TO_IDENTITY.get(state) if state is not None else None
        if state_identity is not None:
            item["power-state"] = {"oper": state_identity}

        relationship_groups = relationships_by_object.get(energy_object.energy_object_id, {})
        if relationship_groups:
            item["relationship"] = [
                {
                    "type": _RELATION_TO_IDENTITY[relationship_type],
                    "peer": sorted(peers, key=lambda peer: peer["id"]),
                }
                for relationship_type, peers in sorted(
                    relationship_groups.items(), key=lambda entry: entry[0].value
                )
            ]
        yang_energy_objects.append(item)

    return {
        f"{HARDWARE_MODULE}:hardware": {"component": components},
        f"{GREEN_MODULE}:energy-objects": {"energy-object": yang_energy_objects},
    }


def from_yang_instance(
    instance: Mapping[str, object],
    *,
    device_id: str,
    device_ids_by_energy_object: Mapping[str, str] | None = None,
) -> tuple[tuple[EnergyObject, ...], tuple[EnergyRelationship, ...]]:
    """Read RFC 7951 data, applying device IDs from controller-side correlation.

    RFC 8348 hardware is scoped to one managed system and the GREEN module
    carries no device_id leaf. Multi-device controller identity is therefore
    supplied out-of-band rather than added to the standard YANG tree.
    """
    hardware_root = instance.get(f"{HARDWARE_MODULE}:hardware", {})
    energy_root = instance.get(f"{GREEN_MODULE}:energy-objects", {})
    if not isinstance(hardware_root, Mapping) or not isinstance(energy_root, Mapping):
        raise ValueError("instance must contain hardware and energy-objects containers")

    hardware_components = hardware_root.get("component", [])
    yang_objects = energy_root.get("energy-object", [])
    if not isinstance(hardware_components, list) or not isinstance(yang_objects, list):
        raise ValueError("hardware/component and energy-object must be lists")

    components_by_name: dict[str, Mapping[str, object]] = {}
    for component in hardware_components:
        if not isinstance(component, Mapping) or not isinstance(component.get("name"), str):
            raise ValueError("each hardware component must have a string name")
        name = component["name"]
        if name in components_by_name:
            raise ValueError(f"duplicate hardware component name: {name}")
        components_by_name[name] = component

    energy_objects: list[EnergyObject] = []
    relationships: list[EnergyRelationship] = []
    seen_object_ids: set[str] = set()
    for item in yang_objects:
        if not isinstance(item, Mapping) or not isinstance(item.get("id"), str):
            raise ValueError("each Energy Object must have a string id")
        energy_object_id = item["id"]
        if energy_object_id in seen_object_ids:
            raise ValueError(f"duplicate Energy Object ID: {energy_object_id}")
        seen_object_ids.add(energy_object_id)

        component_name = item.get("source-component-id")
        if component_name is not None and not isinstance(component_name, str):
            raise ValueError("source-component-id must be a string")
        component = components_by_name.get(component_name) if component_name else None
        if component_name and component is None:
            raise ValueError(
                f"source-component-id references unknown hardware name: {component_name}"
            )
        hardware_uuid = component.get("uuid") if component is not None else None
        if hardware_uuid is not None and not isinstance(hardware_uuid, str):
            raise ValueError("hardware component uuid must be a string")
        hardware_parent_name = component.get("parent") if component is not None else None
        if hardware_parent_name is not None and not isinstance(hardware_parent_name, str):
            raise ValueError("hardware component parent must be a string")

        energy_objects.append(
            EnergyObject(
                device_id=(device_ids_by_energy_object or {}).get(energy_object_id, device_id),
                energy_object_id=energy_object_id,
                hardware_component_name=component_name,
                hardware_component_uuid=hardware_uuid,
                hardware_parent_name=hardware_parent_name,
            )
        )

        yang_relationships = item.get("relationship", [])
        if not isinstance(yang_relationships, list):
            raise ValueError("relationship must be a list")
        for relation in yang_relationships:
            if not isinstance(relation, Mapping) or not isinstance(relation.get("type"), str):
                raise ValueError("each relationship must have a string identity type")
            relationship_identity = relation["type"]
            relationship_type = _IDENTITY_TO_RELATION.get(relationship_identity)
            if relationship_type is None:
                raise ValueError(f"unsupported GREEN relationship identity: {relationship_identity}")
            peers = relation.get("peer", [])
            if not isinstance(peers, list):
                raise ValueError("relationship peer must be a list")
            for peer in peers:
                if not isinstance(peer, Mapping) or not isinstance(peer.get("id"), str):
                    raise ValueError("each relationship peer must have a string id")
                peer_id = peer["id"]
                details = peer.get("details", "yang-instance")
                if not isinstance(details, str):
                    raise ValueError("relationship details must be a string")
                relationships.append(
                    EnergyRelationship(
                        relationship_id=(
                            f"{energy_object_id}:{relationship_type.value}:{peer_id}"
                        ),
                        relationship_type=relationship_type,
                        source_energy_object_id=energy_object_id,
                        peer_energy_object_id=peer_id,
                        provenance=details,
                    )
                )

    return tuple(energy_objects), tuple(relationships)