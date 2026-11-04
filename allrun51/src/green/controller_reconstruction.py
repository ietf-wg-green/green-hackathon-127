from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET

from green.controller_identity import ComponentIdentity, EnergyObjectIdentity
from green.models import EnergyObject, EnergyRelationship
from green.yang_adapter import from_yang_instance


HARDWARE_NS = "urn:ietf:params:xml:ns:yang:ietf-hardware"
GREEN_NS = "urn:ietf:params:xml:ns:yang:ietf-power-and-energy"


@dataclass(frozen=True)
class ReconstructedTopology:
    device_id: str
    energy_objects: tuple[EnergyObject, ...]
    relationships: tuple[EnergyRelationship, ...]

    @property
    def component_identities(self) -> frozenset[ComponentIdentity]:
        return frozenset(
            ComponentIdentity(item.device_id, item.hardware_component_name)
            for item in self.energy_objects
            if item.hardware_component_name is not None
        )

    @property
    def energy_object_identities(self) -> frozenset[EnergyObjectIdentity]:
        return frozenset(
            EnergyObjectIdentity(item.device_id, item.energy_object_id)
            for item in self.energy_objects
        )


def reconstruct_from_netconf_xml(xml_reply: str, *, device_id: str) -> ReconstructedTopology:
    """Reconstruct inventory solely from a NETCONF reply's YANG-visible data."""
    root = ET.fromstring(xml_reply)
    hardware_components = []
    for component in root.findall(f".//{{{HARDWARE_NS}}}component"):
        item = {"name": _leaf(component, HARDWARE_NS, "name")}
        for field in ("class", "uuid", "parent"):
            value = _leaf(component, HARDWARE_NS, field)
            if value is not None:
                item[field] = value
        hardware_components.append(item)

    energy_objects = []
    for energy_object in root.findall(f".//{{{GREEN_NS}}}energy-object"):
        item = {"id": _leaf(energy_object, GREEN_NS, "id")}
        component_id = _leaf(energy_object, GREEN_NS, "source-component-id")
        if component_id is not None:
            item["source-component-id"] = component_id
        relationships = []
        for relationship in energy_object.findall(f"{{{GREEN_NS}}}relationship"):
            relation_type = _leaf(relationship, GREEN_NS, "type")
            if relation_type is not None and relation_type.startswith("eo:"):
                relation_type = f"ietf-power-and-energy:{relation_type.removeprefix('eo:')}"
            peers = []
            for peer in relationship.findall(f"{{{GREEN_NS}}}peer"):
                peer_id = _leaf(peer, GREEN_NS, "id")
                details = _leaf(peer, GREEN_NS, "details")
                peer_record = {"id": peer_id}
                if details is not None:
                    peer_record["details"] = details
                peers.append(peer_record)
            relationships.append({"type": relation_type, "peer": peers})
        if relationships:
            item["relationship"] = relationships
        energy_objects.append(item)

    instance = {
        "ietf-hardware:hardware": {"component": hardware_components},
        "ietf-power-and-energy:energy-objects": {"energy-object": energy_objects},
    }
    decoded_objects, decoded_relationships = from_yang_instance(
        instance,
        device_id=device_id,
    )
    return ReconstructedTopology(device_id, decoded_objects, decoded_relationships)


def _leaf(parent: ET.Element, namespace: str, name: str) -> str | None:
    node = parent.find(f"{{{namespace}}}{name}")
    return node.text if node is not None else None