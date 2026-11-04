from collections import defaultdict, deque
from collections.abc import Iterable, Sequence

from green.models import (
    AccountingBoundary,
    EnergyObject,
    EnergyRelationship,
    RelationshipType,
)


UPSTREAM_METER_ID = "eo-upstream-meter"
SERVER_A_ID = "eo-server-a"
AI_NODE_1_NIC_ID = "eo-ai-node-1-nic-1"
SERVER_B_ID = "eo-server-b"
ROUTER_A_ID = "eo-router-a"
ROUTER_B_ID = "eo-router-b"
LINECARD_1_ID = "eo-router-a-linecard-1"
LINECARD_2_ID = "eo-router-a-linecard-2"
NON_CRITICAL_PORT_ID = "eo-router-b-switchable-port"
PDU_ID = "eo-pdu-1"
PDU_OUTLET_ID = "eo-pdu-outlet-1"
LEGACY_DEVICE_ID = "eo-legacy-device"
POE_SWITCH_ID = "eo-poe-switch"
POE_PORT_AP1_ID = "eo-poe-port-ap1"
AP_1_ID = "eo-ap-1"
AP_2_ID = "eo-ap-2"
AP_BASEBAND_ID = "eo-ap-baseband"
AP_RADIO_24_ID = "eo-ap-radio-24"
AP_RADIO_5_ID = "eo-ap-radio-5"
DOMAIN_AGGREGATOR_ID = "eo-domain-energy-aggregator"
ACCESS_DOMAIN_ID = "eo-access-domain"
TRANSPORT_DOMAIN_ID = "eo-transport-domain"
CORE_DOMAIN_ID = "eo-core-domain"
NETWORK_AGGREGATOR_ID = "eo-network-energy-aggregator"
ROUTER_C_ID = "eo-router-c"
ISAC_AGGREGATOR_ID = "eo-isac-energy-aggregator"
ROADSIDE_UNIT_ID = "eo-roadside-unit"
RADAR_SENSOR_ID = "eo-radar-sensor"
ISAC_TRANSCEIVER_ID = "eo-isac-transceiver"
CITY_TRAFFIC_CONTROLLER_ID = "eo-city-traffic-controller"
WIRELESS_LINK_ID = "eo-wireless-link-1"
VIDEO_ORIGIN_ID = "eo-video-origin-1"
VIDEO_CACHE_ID = "eo-video-cache-1"
EDGE_ROUTER_ID = ROUTER_A_ID
AI_AGGREGATOR_ID = "eo-ai-cluster-energy-aggregator"
AI_NODE_1_ID = "eo-ai-node-1"
AI_NODE_2_ID = "eo-ai-node-2"
AI_FABRIC_ID = "eo-ai-fabric"
IP_OVERLAY_ID = "eo-ip-overlay"
TRANSPORT_UNDERLAY_ID = "eo-transport-underlay"
TRANSPORT_MODULE_ID = "eo-transport-module"
DEPENDENT_IP_FUNCTION_ID = "eo-dependent-ip-function"
SWITCH_FABRIC_ID = "eo-switch-fabric"
GRID_SOURCE_ID = "eo-grid-source"
BACKUP_BATTERY_ID = "eo-backup-battery"


class RelationshipGraph:
    def __init__(
        self,
        energy_objects: Iterable[EnergyObject],
        relationships: Iterable[EnergyRelationship],
    ) -> None:
        self.energy_objects = tuple(energy_objects)
        self.relationships = tuple(relationships)
        self.objects_by_id = {obj.energy_object_id: obj for obj in self.energy_objects}
        self._metering_edges: dict[str, list[tuple[str, EnergyRelationship]]] = defaultdict(list)
        for relationship in self.relationships:
            edge = self._directed_metering_edge(relationship)
            if edge is not None:
                parent, child = edge
                if parent in self.objects_by_id and child in self.objects_by_id:
                    self._metering_edges[parent].append((child, relationship))
        self.validation_errors = self._validate()

    @property
    def energy_object_ids(self) -> frozenset[str]:
        return frozenset(self.objects_by_id)

    @staticmethod
    def _directed_metering_edge(
        relationship: EnergyRelationship,
    ) -> tuple[str, str] | None:
        if relationship.relationship_type == RelationshipType.METERING:
            return relationship.source_energy_object_id, relationship.peer_energy_object_id
        if relationship.relationship_type == RelationshipType.METERED_BY:
            return relationship.peer_energy_object_id, relationship.source_energy_object_id
        return None

    def _validate(self) -> tuple[str, ...]:
        errors: list[str] = []
        object_ids = [obj.energy_object_id for obj in self.energy_objects]
        if len(set(object_ids)) != len(object_ids):
            errors.append("duplicate energy_object_id in Energy Objects")

        seen_relationships: set[tuple[str, RelationshipType, str]] = set()
        for relationship in self.relationships:
            key = (
                relationship.source_energy_object_id,
                relationship.relationship_type,
                relationship.peer_energy_object_id,
            )
            if relationship.source_energy_object_id == relationship.peer_energy_object_id:
                errors.append(f"relationship {relationship.relationship_id} is a self-relationship")
            if key in seen_relationships:
                errors.append(f"duplicate relationship: {relationship.relationship_id}")
            seen_relationships.add(key)
            if relationship.source_energy_object_id not in self.objects_by_id:
                errors.append(
                    f"relationship {relationship.relationship_id} references unknown source "
                    f"{relationship.source_energy_object_id}"
                )
            if relationship.peer_energy_object_id not in self.objects_by_id:
                errors.append(
                    f"relationship {relationship.relationship_id} references unknown peer "
                    f"{relationship.peer_energy_object_id}"
                )

        colors: dict[str, int] = {}
        stack: list[str] = []
        cycle_errors: set[str] = set()

        def visit(node: str) -> None:
            colors[node] = 1
            stack.append(node)
            for peer, _ in self._metering_edges.get(node, ()):
                if colors.get(peer, 0) == 1:
                    cycle = stack[stack.index(peer):] + [peer]
                    cycle_errors.add(f"metering cycle detected: {' -> '.join(cycle)}")
                elif colors.get(peer, 0) == 0:
                    visit(peer)
            stack.pop()
            colors[node] = 2

        for object_id in self.objects_by_id:
            if colors.get(object_id, 0) == 0:
                visit(object_id)
        errors.extend(sorted(cycle_errors))
        return tuple(errors)

    def metering_paths_from(
        self,
        root_energy_object_id: str,
    ) -> dict[str, tuple[EnergyRelationship, ...]]:
        if root_energy_object_id not in self.objects_by_id:
            return {}
        paths: dict[str, tuple[EnergyRelationship, ...]] = {root_energy_object_id: ()}
        pending = deque([root_energy_object_id])
        while pending:
            parent = pending.popleft()
            for child, relationship in self._metering_edges.get(parent, ()):
                if child not in paths:
                    paths[child] = paths[parent] + (relationship,)
                    pending.append(child)
        paths.pop(root_energy_object_id)
        return paths


def demo_energy_objects() -> tuple[EnergyObject, ...]:
    device_id = "pdu-1"
    return (
        EnergyObject(
            device_id,
            UPSTREAM_METER_ID,
            "upstream-meter",
            "00000000-0000-4000-8000-000000000001",
        ),
        EnergyObject(
            device_id,
            SERVER_A_ID,
            "server-A",
            "00000000-0000-4000-8000-000000000002",
        ),
        EnergyObject(
            device_id,
            SERVER_B_ID,
            "server-B",
            "00000000-0000-4000-8000-000000000003",
        ),
        EnergyObject(
            "router-A",
            ROUTER_A_ID,
            "router-A",
            "00000000-0000-4000-8000-000000000010",
        ),
        EnergyObject(
            "router-A",
            LINECARD_1_ID,
            "linecard-1",
            "00000000-0000-4000-8000-000000000011",
            "router-A",
        ),
        EnergyObject(
            "router-A",
            LINECARD_2_ID,
            "linecard-2",
            "00000000-0000-4000-8000-000000000012",
            "router-A",
        ),
        EnergyObject(
            "router-B",
            ROUTER_B_ID,
            "router-B",
            "00000000-0000-4000-8000-000000000020",
        ),
        EnergyObject(
            "router-B",
            NON_CRITICAL_PORT_ID,
            "switchable-port",
            "00000000-0000-4000-8000-000000000021",
            "router-B",
        ),
        *_additional_energy_objects(),
    )


def _additional_energy_objects() -> tuple[EnergyObject, ...]:
    specs = (
        ("pdu-1", PDU_ID, "pdu-1", 30, None),
        ("pdu-1", PDU_OUTLET_ID, "pdu-outlet-1", 31, "pdu-1"),
        ("ai-training-node-1", AI_NODE_1_NIC_ID, "ai-node-1-nic", 112, "ai-node-1"),
        ("legacy-device-1", LEGACY_DEVICE_ID, "legacy-device", 32, None),
        ("wlan-1", POE_SWITCH_ID, "poe-switch", 40, None),
        ("wlan-1", POE_PORT_AP1_ID, "poe-port-ap1", 41, "poe-switch"),
        ("wlan-1", AP_1_ID, "ap-1", 42, None),
        ("wlan-2", AP_2_ID, "ap-2", 43, None),
        ("wlan-1", AP_BASEBAND_ID, "ap-baseband", 44, "ap-1"),
        ("wlan-1", AP_RADIO_24_ID, "ap-radio-24", 45, "ap-baseband"),
        ("wlan-1", AP_RADIO_5_ID, "ap-radio-5", 46, "ap-baseband"),
        ("cross-domain-controller", DOMAIN_AGGREGATOR_ID, "domain-energy-aggregator", 50, None),
        ("access-domain-controller", ACCESS_DOMAIN_ID, "access-domain", 51, None),
        ("transport-domain-controller", TRANSPORT_DOMAIN_ID, "transport-domain", 52, None),
        ("core-domain-controller", CORE_DOMAIN_ID, "core-domain", 53, None),
        ("network-controller", NETWORK_AGGREGATOR_ID, "network-energy-aggregator", 54, None),
        ("router-C", ROUTER_C_ID, "router-C", 55, None),
        ("smart-city-controller", ISAC_AGGREGATOR_ID, "isac-energy-aggregator", 60, None),
        ("smart-city-site-1", ROADSIDE_UNIT_ID, "roadside-unit-1", 61, None),
        ("smart-city-site-1", RADAR_SENSOR_ID, "radar-sensor-1", 62, "roadside-unit-1"),
        ("smart-city-site-1", ISAC_TRANSCEIVER_ID, "isac-transceiver-1", 63, "roadside-unit-1"),
        ("smart-city-controller", CITY_TRAFFIC_CONTROLLER_ID, "city-traffic-controller", 64, None),
        ("microwave-site-1", WIRELESS_LINK_ID, "wireless-link-1", 70, None),
        ("video-service", VIDEO_ORIGIN_ID, "video-origin-1", 80, None),
        ("video-service", VIDEO_CACHE_ID, "video-cache-1", 81, None),
        ("ai-training-cluster", AI_AGGREGATOR_ID, "ai-cluster-energy-aggregator", 90, None),
        ("ai-training-node-1", AI_NODE_1_ID, "ai-node-1", 91, None),
        ("ai-training-node-2", AI_NODE_2_ID, "ai-node-2", 92, None),
        ("ai-training-cluster", AI_FABRIC_ID, "ai-fabric", 93, None),
        ("multilayer-controller", IP_OVERLAY_ID, "ip-overlay", 100, None),
        ("multilayer-controller", TRANSPORT_UNDERLAY_ID, "transport-underlay", 101, None),
        ("transport-site-1", TRANSPORT_MODULE_ID, "transport-module", 102, None),
        ("multilayer-controller", DEPENDENT_IP_FUNCTION_ID, "dependent-ip-function", 103, None),
        ("router-A", SWITCH_FABRIC_ID, "switch-fabric", 104, "router-A"),
        ("power-grid", GRID_SOURCE_ID, "grid-source", 110, None),
        ("power-backup", BACKUP_BATTERY_ID, "backup-battery", 111, None),
    )
    return tuple(
        EnergyObject(
            device_id=device_id,
            energy_object_id=energy_object_id,
            hardware_component_name=component_name,
            hardware_component_uuid=f"00000000-0000-4000-8000-{uuid_suffix:012d}",
            hardware_parent_name=parent_name,
        )
        for device_id, energy_object_id, component_name, uuid_suffix, parent_name in specs
    )


def demo_metering_relationships() -> tuple[EnergyRelationship, ...]:
    provenance = "explicit-demo-topology"
    return (
        EnergyRelationship(
            "rel-meter-server-a",
            RelationshipType.METERING,
            UPSTREAM_METER_ID,
            SERVER_A_ID,
            provenance,
        ),
        EnergyRelationship(
            "rel-meter-server-b",
            RelationshipType.METERING,
            UPSTREAM_METER_ID,
            SERVER_B_ID,
            provenance,
        ),
    )


def demo_accounting_boundary() -> AccountingBoundary:
    return AccountingBoundary(
        "rack-1",
        UPSTREAM_METER_ID,
        (UPSTREAM_METER_ID, SERVER_A_ID, SERVER_B_ID),
    )


def build_demo_topology(
    *,
    include_metering: bool = True,
    relationships: Sequence[EnergyRelationship] | None = None,
) -> tuple[RelationshipGraph, AccountingBoundary]:
    if relationships is None:
        selected_relationships = demo_metering_relationships() if include_metering else ()
    else:
        selected_relationships = tuple(relationships)
    graph = RelationshipGraph(demo_energy_objects(), selected_relationships)
    return graph, demo_accounting_boundary()