from __future__ import annotations

from pathlib import Path

from green.canonical_network import load_canonical_network
from green.markdown_tables import align_markdown_tables
from green.topology import demo_energy_objects


CAPABILITY_DEMO_SELECTIONS = (
    (
        "eo-router-a-linecard-1",
        ("UC 2.1", "UC 2.2", "UC 2.10", "UC 2.11", "UC 2.16"),
        "router-linecard",
        "Stable line-card identity supports a future router power-state profile.",
    ),
    (
        "eo-ap-baseband",
        ("UC 2.9",),
        "ap-baseband",
        "Stable AP subsystem identity for future radio/baseband profiles.",
    ),
    (
        "eo-ap-radio-24",
        ("UC 2.9",),
        "ap-radio",
        "Existing 2.4 GHz radio component exercises per-radio power modes.",
    ),
    (
        "eo-ap-radio-5",
        ("UC 2.9",),
        "ap-radio",
        "Existing 5 GHz radio component exercises per-radio power modes.",
    ),
    (
        "eo-transport-module",
        ("UC 2.7", "UC 2.16"),
        "transport-radio-module",
        "Transport module anchors future underlay and radio capability profiles.",
    ),
    (
        "eo-ai-node-1-nic-1",
        ("UC 2.15",),
        "server-nic",
        "Stable compute-node NIC identity is separate from workload event state.",
    ),
    (
        "eo-radar-sensor",
        ("UC 2.12",),
        "isac-sensing-component",
        "Existing radar sensor is an ISAC sensing capability attachment point.",
    ),
)

TOPOLOGY_LABELS = {
    "T1-fixed-network": "T1 CORE",
    "T2-wlan-poe": "T2 AIR",
    "T3-power-infrastructure": "T3 POWER",
    "T4-wireless-transport": "T4 BACKHAUL",
    "T5-edge-compute": "T5 EDGE",
    "T6-isac-smart-city": "T6 CITY",
}


def readiness_rows() -> list[dict[str, str]]:
    network = load_canonical_network()
    objects = {item.energy_object_id: item for item in demo_energy_objects()}
    rows = []
    for energy_object_id, ucs, profile_class, reason in CAPABILITY_DEMO_SELECTIONS:
        energy_object = objects[energy_object_id]
        device = network.devices_by_id[energy_object.device_id]
        selected_topology_ids = {
            topology_id
            for uc in ucs
            for topology_id in network.scenarios_by_uc[uc].topology_ids
        }
        topology_ids = [
            topology.topology_id
            for topology in network.topologies
            if topology.topology_id in selected_topology_ids
            and energy_object.device_id in topology.device_ids
        ]
        topology_summary = [TOPOLOGY_LABELS[topology_id] for topology_id in topology_ids]
        relationships = []
        for item in network.relationship_behaviors:
            relationship = item.relationship
            if energy_object_id not in {
                relationship.source_energy_object_id,
                relationship.peer_energy_object_id,
            }:
                continue
            source = objects[relationship.source_energy_object_id]
            peer = objects[relationship.peer_energy_object_id]
            relationships.append(
                f"{source.energy_object_id} {relationship.relationship_type.value} {peer.energy_object_id}"
            )
        rows.append(
            {
                "uc": ", ".join(ucs),
                "hardware_component_name": energy_object.hardware_component_name or "",
                "hardware_component_uuid": energy_object.hardware_component_uuid or "",
                "device_id": energy_object.device_id,
                "device_archetype": device.archetype_id,
                "topology": ", ".join(topology_ids),
                "topology_summary": ", ".join(topology_summary),
                "energy_object_id": energy_object.energy_object_id,
                "source_component_id": energy_object.hardware_component_name or "",
                "relevant_relationships": "; ".join(sorted(relationships)) or "none currently modeled",
                "future_capability_profile_class": profile_class,
                "reason": reason,
            }
        )
    return rows


def render_readiness_document() -> str:
    rows = readiness_rows()
    lines = [
        "# Capability-Discovery Readiness for Future caprun",
        "",
        "This is a stable-identity readiness inventory only. allrun51 does not implement RFC 9196, `ietf-system-capabilities`, `ietf-power-state-capabilities`, capability callbacks, or capability-gated control. UC 2.11 classification remains simulator/controller metadata.",
        "",
        "The selected Energy Objects map to RFC 8348 Components by the existing `source-component-id` leafref. Device ID, component name, UUID, and Energy Object ID remain distinct.",
        "",
        "| Hardware component | Profile class | UCs | Topology |",
        "| --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| `{name}` | `{profile}` | {ucs} | {topology} |".format(
                name=row["hardware_component_name"],
                topology=row["topology_summary"],
                ucs=row["uc"],
                profile=row["future_capability_profile_class"],
            )
        )
    lines.extend(["", "## Component Details", ""])
    for row in rows:
        lines.extend([
            f"### {row['energy_object_id']} ({row['hardware_component_name']})",
            "",
            f"- Device ID: `{row['device_id']}`",
            f"- Hardware component name: `{row['hardware_component_name']}`",
            f"- Hardware component UUID: `{row['hardware_component_uuid']}`",
            f"- Device archetype: `{row['device_archetype']}`",
            f"- Topology: {row['topology']}",
            f"- Energy Object ID: `{row['energy_object_id']}`",
            f"- source-component-id: `{row['source_component_id']}`",
            f"- UCs: {row['uc']}",
            f"- Future capability-profile class: `{row['future_capability_profile_class']}`",
            f"- Reason: {row['reason']}",
            "- Relevant GREEN relationships:",
        ])
        relationships = [
            item.strip()
            for item in row["relevant_relationships"].split(";")
            if item.strip()
        ]
        lines.extend(
            [f"  - {relationship}" for relationship in relationships]
            if relationships
            else ["  - none currently modeled"]
        )
        lines.append("")
    lines.extend(
        [
            "",
            "Future capability data belongs to a separate caprun increment. No RFC 9196 capability values are implemented or implied here.",
            "",
        ]
    )
    return "\n".join(lines)


def write_readiness_document(destination: Path | None = None) -> Path:
    target = destination or Path(__file__).resolve().parents[2] / "docs" / "capability_discovery_readiness.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(align_markdown_tables(render_readiness_document()), encoding="utf-8")
    return target
