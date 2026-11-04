from __future__ import annotations

from pathlib import Path

from green.canonical_network import (
    KNOWLEDGE_OBSERVABILITY,
    PHYSICAL_DYNAMIC,
    STABLE_STRUCTURAL,
    load_canonical_network,
)
from green.catalog import UC_CATALOG
from green.energy_observability import write_observability_document
from green.markdown_tables import align_markdown_directory, align_markdown_tables


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def render_canonical_network() -> str:
    network = load_canonical_network()
    device_names = {item.device_id: item.name for item in network.device_instances}
    topology_labels = {
        "T1-fixed-network": "T1 CORE",
        "T2-wlan-poe": "T2 AIR",
        "T3-power-infrastructure": "T3 POWER",
        "T4-wireless-transport": "T4 BACKHAUL",
        "T5-edge-compute": "T5 EDGE",
        "T6-isac-smart-city": "T6 CITY",
    }
    lines = [
        "# Canonical Demo Network",
        "",
        f"`{network.network_id}` is one stable logical network composed of {len(network.topologies)} reusable sub-topologies.",
        "",
        "| Topology | Name | Devices | Energy Objects |",
        "| --- | --- | ---: | ---: |",
    ]
    for topology in network.topologies:
        lines.append(
            f"| {topology_labels[topology.topology_id]} | {topology.name} | {len(topology.device_ids)} | {len(topology.energy_object_ids)} |"
        )
    lines.extend([
        "",
        "Sub-topologies may share a stable device instance; the UC mapping selects a primary view and optional supporting views without cloning the device inventory.",
        "RFC 8348 containment and GREEN Energy Object relationships are modeled separately. The topology registry supplies stable identities; event definitions supply only dynamic overlays.",
        "",
        "## Topology Details",
        "",
    ])
    for topology in network.topologies:
        lines.extend([
            f"### {topology_labels[topology.topology_id]} - {topology.name}",
            "",
            f"Topology ID: `{topology.topology_id}`.",
            "",
            "Device instances:",
        ])
        lines.extend(
            f"- `{device_id}` - {device_names[device_id]}"
            for device_id in topology.device_ids
        )
        lines.extend([
            f"Relationship profiles: {', '.join(topology.relationship_profiles)}.",
            "",
        ])
    return "\n".join(lines)


def render_device_archetypes() -> str:
    network = load_canonical_network()
    devices_by_archetype: dict[str, list[str]] = {
        item.archetype_id: [] for item in network.archetypes
    }
    for device in network.device_instances:
        devices_by_archetype[device.archetype_id].append(device.device_id)
    lines = [
        "# Device Archetypes and Instances",
        "",
        "Archetypes define reusable device classes; instances provide stable `device_id` values. Hardware Components and Energy Objects remain separate identities below those instances.",
        "",
        "| Archetype | Name | Role count | Instance count |",
        "| --- | --- | ---: | ---: |",
    ]
    for archetype in network.archetypes:
        lines.append(
            f"| {archetype.archetype_id} | {archetype.name} | {len(archetype.component_roles)} | {len(devices_by_archetype[archetype.archetype_id])} |"
        )
    lines.extend(["", "## Archetype Details", ""])
    for archetype in network.archetypes:
        lines.extend([
            f"### {archetype.archetype_id} - {archetype.name}",
            "",
            f"Component roles: {', '.join(archetype.component_roles)}.",
            "",
            "Device instances:",
        ])
        lines.extend(
            f"- `{device_id}`"
            for device_id in sorted(devices_by_archetype[archetype.archetype_id])
        )
        lines.append("")
    lines.extend(["UC scenarios never redefine or rename a device instance.", ""])
    return "\n".join(lines)


def render_uc_topology_matrix() -> str:
    network = load_canonical_network()
    scenarios = network.scenarios_by_uc
    use_cases = {item.series.value: item for item in UC_CATALOG}
    lines = [
        "# UC-to-Topology Matrix",
        "",
        "## Use Case Names",
        "",
        "| UC | Name |",
        "| --- | --- |",
    ]
    for uc in sorted(scenarios, key=_uc_order):
        scenario = scenarios[uc]
        use_case = use_cases[uc]
        lines.append(f"| {uc} | {use_case.title} |")
    lines.extend([
        "",
        "## Topology Assignment Summary",
        "",
        "| UC | Primary | Secondary | Events |",
        "| --- | --- | --- | ---: |",
    ])
    topology_labels = {
        "T1-fixed-network": "T1 CORE",
        "T2-wlan-poe": "T2 AIR",
        "T3-power-infrastructure": "T3 POWER",
        "T4-wireless-transport": "T4 BACKHAUL",
        "T5-edge-compute": "T5 EDGE",
        "T6-isac-smart-city": "T6 CITY",
    }
    for uc in sorted(scenarios, key=_uc_order):
        scenario = scenarios[uc]
        use_case = use_cases[uc]
        primary = "All (T1-T6)" if uc == "UC 2.11" else ", ".join(topology_labels[item] for item in scenario.primary)
        secondary = ", ".join(topology_labels[item] for item in scenario.secondary) or "-"
        lines.append(
            f"| {uc} | {primary} | {secondary} | {len(use_case.events)} |"
        )
    lines.extend(["", "UC 2.11 uses the full canonical network. Group B UCs 2.3 and 2.4 remain deferred.", ""])
    return "\n".join(lines)


def render_controller_identity_model() -> str:
    return "\n".join([
        "# Controller Identity Model",
        "",
        "Controller identity is scoped by the managed device, not by a locally unique label alone.",
        "",
        "```text",
        "ComponentIdentity = (device_id, hardware_component_name)",
        "EnergyObjectIdentity = (device_id, energy_object_id)",
        "hardware_component_uuid remains a separate stable property",
        "```",
        "",
        "For example, `ComponentIdentity(\"router-A\", \"linecard-1\")` and `ComponentIdentity(\"router-B\", \"linecard-1\")` are distinct. A UUID is never substituted for a component name, Energy Object ID, or device ID.",
        "",
        "RFC 8348 and `ietf-power-and-energy` do not define a GREEN `device_id` leaf. A controller obtains the device scope from the NETCONF managed-system/session identity and applies it out of band when reconstructing these keys. No device-side YANG change is required.",
        "",
    ])


def render_relationship_behavior_classes() -> str:
    network = load_canonical_network()
    counts: dict[str, int] = {}
    types_by_class: dict[str, set[str]] = {}
    for item in network.relationship_behaviors:
        counts[item.behavior_class] = counts.get(item.behavior_class, 0) + 1
        types_by_class.setdefault(item.behavior_class, set()).add(
            item.relationship.relationship_type.value
        )
    descriptions = {
        STABLE_STRUCTURAL: "Persistent functional structure, including aggregation and enabling dependencies.",
        PHYSICAL_DYNAMIC: "The active electrical source path; UC 2.14 changes grid/battery links as state changes.",
        KNOWLEDGE_OBSERVABILITY: "Physical metering links whose controller visibility can be incomplete or discovered later.",
    }
    lines = [
        "# Relationship Behavior Classes",
        "",
        "| Behavior class | Links | Relationship types |",
        "| --- | ---: | --- |",
    ]
    for behavior_class in (STABLE_STRUCTURAL, PHYSICAL_DYNAMIC, KNOWLEDGE_OBSERVABILITY):
        lines.append(
            f"| {behavior_class} | {counts.get(behavior_class, 0)} | {', '.join(sorted(types_by_class.get(behavior_class, set())))} |"
        )
    lines.extend([
        "",
        "## Class Semantics",
        "",
        *[f"- `{name}`: {description}" for name, description in descriptions.items()],
        "",
        "Hardware `parent` containment does not imply metering, aggregation, powering, or enabling.",
        "",
        "## UC 2.13 Discovery",
        "",
        "The canonical physical metering topology exists independently of controller visibility. U13-0 keeps the actual links in the topology truth set while exposing no metering links to the event observer; later discovery overlays expose the links. Accounting uses only event-visible relationships, so incomplete knowledge remains incomplete rather than fabricating a physical topology change.",
        "",
    ])
    return "\n".join(lines)


def render_future_capability_profile_model() -> str:
    return "\n".join([
        "# Future Capability Profile Model",
        "",
        "Future capability data belongs to stable device archetypes or hardware component instances, joined by RFC 8348 identity. It does not belong to UC names or event IDs.",
        "",
        "| Capability profile class | Attachment point in allrun51 |",
        "| --- | --- |",
        "| router-linecard | fixed-router / `linecard-1` Component |",
        "| ap-radio | WLAN access / `ap-radio-24` or `ap-radio-5` Component |",
        "| ap-baseband | WLAN access / `ap-baseband` Component |",
        "| transport-radio-module | wireless transport / `transport-module` Component |",
        "| server-nic | compute node / `ai-node-1-nic` Component |",
        "| isac-sensing-component | ISAC roadside unit / `radar-sensor-1` Component |",
        "",
        "Bad: UC 2.10 capability profile or U16-6 capability profile. Good: router-linecard or transport-radio-module profile.",
        "",
        "allrun51 implements readiness metadata only. It does not implement RFC 9196, `ietf-system-capabilities`, `ietf-power-state-capabilities`, or capability values, and does not derive capability from operational UC state.",
        "",
    ])


def write_canonical_documents(project_root: Path | None = None) -> tuple[Path, ...]:
    root = project_root or PROJECT_ROOT
    docs = root / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    renderers = {
        "canonical_network.md": render_canonical_network,
        "device_archetypes.md": render_device_archetypes,
        "uc_topology_matrix.md": render_uc_topology_matrix,
        "controller_identity_model.md": render_controller_identity_model,
        "relationship_behavior_classes.md": render_relationship_behavior_classes,
        "future_capability_profile_model.md": render_future_capability_profile_model,
    }
    paths = []
    for filename, renderer in renderers.items():
        path = docs / filename
        path.write_text(renderer(), encoding="utf-8")
        paths.append(path)
    paths.append(write_observability_document(docs / "energy_object_observability.md"))
    align_markdown_directory(docs)
    return tuple(paths)


def _uc_order(uc: str) -> tuple[int, int]:
    major, minor = uc.removeprefix("UC ").split(".")
    return int(major), int(minor)