import json
import os
import socket
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from green.catalog import USE_CASES_BY_SERIES
from green.models import AccountingResult, EnergyObject, SimulatedEvent
from green.netconf_trace import (
    _energy_object_inventory,
    _hardware_inventory,
    filter_yang_instance_to_energy_objects,
)
from green.yang_adapter import to_yang_instance


def event_to_yang(event: SimulatedEvent, energy_objects: tuple[EnergyObject, ...]) -> dict[str, object]:
    return to_yang_instance(
        energy_objects,
        event.relationships,
        event.measurements,
        event.component_states,
        event.power_measurements,
    )


def render_summary(
    event: SimulatedEvent,
    data: dict[str, object],
    visible_energy_object_ids: set[str] | frozenset[str] | None = None,
) -> str:
    energy_root = data.get("ietf-power-and-energy:energy-objects", {})
    all_objects = energy_root.get("energy-object", []) if isinstance(energy_root, dict) else []
    objects_by_id = {
        str(item["id"]): item
        for item in all_objects
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    component_to_object = {
        str(item.get("source-component-id")): object_id
        for object_id, item in objects_by_id.items()
        if item.get("source-component-id")
    }
    selected_ids = {
        object_id
        for object_id, _ in event.component_states
    }
    selected_ids.update(item.energy_object_id for item in event.measurements)
    selected_ids.update(item.energy_object_id for item in event.power_measurements)
    for relationship in event.relationships:
        selected_ids.add(relationship.source_energy_object_id)
        selected_ids.add(relationship.peer_energy_object_id)
    for _, value in event.metadata:
        if value in objects_by_id:
            selected_ids.add(value)
        if value in component_to_object:
            selected_ids.add(component_to_object[value])
        for value_part in value.split(","):
            if value_part in component_to_object:
                selected_ids.add(component_to_object[value_part])
    if visible_energy_object_ids is not None:
        selected_ids = set(visible_energy_object_ids)

    selected_objects = [
        item for object_id, item in objects_by_id.items() if object_id in selected_ids
    ]
    selected_names = {
        str(item.get("source-component-id"))
        for item in selected_objects
        if item.get("source-component-id")
    }
    hardware_root = data.get("ietf-hardware:hardware", {})
    all_components = hardware_root.get("component", []) if isinstance(hardware_root, dict) else []
    components_by_name = {
        str(item["name"]): item
        for item in all_components
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    pending = list(selected_names)
    while pending:
        component = components_by_name.get(pending.pop())
        if not component:
            continue
        parent = component.get("parent")
        if isinstance(parent, str) and parent not in selected_names:
            selected_names.add(parent)
            pending.append(parent)
    summary_data = {
        "ietf-hardware:hardware": {
            "component": [item for name, item in components_by_name.items() if name in selected_names]
        },
        "ietf-power-and-energy:energy-objects": {"energy-object": selected_objects},
    }
    hardware_rows = _hardware_inventory(summary_data) or ["HARDWARE INVENTORY", "(no related hardware)"]
    energy_rows = _energy_object_inventory(summary_data) or ["GREEN ENERGY OBJECTS", "(no related Energy Objects)"]
    sections = [
        "1. HARDWARE INVENTORY",
        *hardware_rows[1:],
        "",
        "2. ENERGY OBJECTS",
        *energy_rows[1:],
        "",
        "3. ENERGY RELATIONSHIPS",
        render_relationships(summary_data),
        "",
        "4. UC-SPECIFIC INTERPRETATION",
        render_interpretation(event),
    ]
    return "\n".join(sections)


def render_compact_event(
    event: SimulatedEvent,
    energy_objects: tuple[EnergyObject, ...],
    previous: SimulatedEvent | None,
    accounting: AccountingResult | None = None,
    visible_energy_object_ids: set[str] | frozenset[str] | None = None,
) -> str:
    objects_by_id = {item.energy_object_id: item for item in energy_objects}
    states = dict(event.component_states)
    related_ids: set[str] = set()
    related_ids.update(item.energy_object_id for item in event.measurements)
    related_ids.update(item.energy_object_id for item in event.power_measurements)
    for relationship in event.relationships:
        related_ids.add(relationship.source_energy_object_id)
        related_ids.add(relationship.peer_energy_object_id)
    if previous is None:
        related_ids.update(states)
    else:
        previous_states = dict(previous.component_states)
        related_ids.update(
            object_id
            for object_id in previous_states.keys() | states.keys()
            if previous_states.get(object_id) != states.get(object_id)
        )
    if visible_energy_object_ids is not None:
        related_ids.intersection_update(visible_energy_object_ids)

    def component_name(object_id: str) -> str:
        item = objects_by_id.get(object_id)
        return item.hardware_component_name if item and item.hardware_component_name else object_id

    hardware = [
        f"{component_name(object_id)}={state.value}"
        for object_id, state in event.component_states
        if object_id in related_ids
    ]
    energy = []
    for measurement in event.measurements:
        if visible_energy_object_ids is not None and measurement.energy_object_id not in visible_energy_object_ids:
            continue
        label = f"{measurement.energy_object_id}[{component_name(measurement.energy_object_id)}]"
        value = f"{measurement.interval_energy_wh}Wh"
        if measurement.cumulative_energy_wh is not None:
            value += f"/total={measurement.cumulative_energy_wh}Wh"
        state = states.get(measurement.energy_object_id)
        if state is not None:
            value += f"/{state.value}"
        energy.append(f"{label}={value}")
    for measurement in event.power_measurements:
        if visible_energy_object_ids is not None and measurement.energy_object_id not in visible_energy_object_ids:
            continue
        label = f"{measurement.energy_object_id}[{component_name(measurement.energy_object_id)}]"
        state = states.get(measurement.energy_object_id)
        value = f"{measurement.instantaneous_power_w}W/{state.value}" if state else f"{measurement.instantaneous_power_w}W"
        energy.append(f"{label}={value}")

    grouped_relationships: dict[tuple[str, str], set[str]] = {}
    for relationship in event.relationships:
        if visible_energy_object_ids is not None and (
            relationship.source_energy_object_id not in visible_energy_object_ids
            or relationship.peer_energy_object_id not in visible_energy_object_ids
        ):
            continue
        key = (relationship.source_energy_object_id, relationship.relationship_type.value.upper())
        grouped_relationships.setdefault(key, set()).add(relationship.peer_energy_object_id)
    relationship_line = "; ".join(
        f"{source} {kind} -> {','.join(sorted(peers))}"
        for (source, kind), peers in sorted(grouped_relationships.items())
    ) or "none"

    changes: list[str] = []
    if previous is None:
        changes.append("initial")
    else:
        previous_states = dict(previous.component_states)
        for object_id in sorted(previous_states.keys() | states.keys()):
            if visible_energy_object_ids is not None and object_id not in visible_energy_object_ids:
                continue
            before, after = previous_states.get(object_id), states.get(object_id)
            if before != after:
                changes.append(f"{component_name(object_id)}:{before.value if before else '-'}->{after.value if after else '-'}")
        previous_power = {item.energy_object_id: item.instantaneous_power_w for item in previous.power_measurements}
        current_power = {item.energy_object_id: item.instantaneous_power_w for item in event.power_measurements}
        for object_id in sorted(previous_power.keys() | current_power.keys()):
            if visible_energy_object_ids is not None and object_id not in visible_energy_object_ids:
                continue
            before, after = previous_power.get(object_id), current_power.get(object_id)
            if before != after:
                changes.append(f"{object_id}:{before if before is not None else '-'}->{after if after is not None else '-'}W")
        previous_energy = {item.energy_object_id: item.interval_energy_wh for item in previous.measurements}
        current_energy = {item.energy_object_id: item.interval_energy_wh for item in event.measurements}
        for object_id in sorted(previous_energy.keys() | current_energy.keys()):
            if visible_energy_object_ids is not None and object_id not in visible_energy_object_ids:
                continue
            before, after = previous_energy.get(object_id), current_energy.get(object_id)
            if before != after:
                changes.append(f"{object_id}:{before if before is not None else '-'}->{after if after is not None else '-'}Wh")
        previous_relationships = {
            (item.source_energy_object_id, item.relationship_type.value.upper(), item.peer_energy_object_id)
            for item in previous.relationships
            if visible_energy_object_ids is None or (
                item.source_energy_object_id in visible_energy_object_ids
                and item.peer_energy_object_id in visible_energy_object_ids
            )
        }
        current_relationships = {
            (item.source_energy_object_id, item.relationship_type.value.upper(), item.peer_energy_object_id)
            for item in event.relationships
            if visible_energy_object_ids is None or (
                item.source_energy_object_id in visible_energy_object_ids
                and item.peer_energy_object_id in visible_energy_object_ids
            )
        }
        changes.extend(
            f"+{source} {kind}->{peer}" for source, kind, peer in sorted(current_relationships - previous_relationships)
        )
        changes.extend(
            f"-{source} {kind}->{peer}" for source, kind, peer in sorted(previous_relationships - current_relationships)
        )
        if not changes:
            changes.append("no observed change")
    if len(changes) > 4:
        changes = changes[:4] + [f"+{len(changes) - 4} more"]

    lines = [
        f"[{event.series.value} / {event.sequence}] {event.name}",
        event.explanation,
        f"HW     {'  '.join(hardware) if hardware else 'no observed state'}",
        f"ENERGY {'  '.join(energy) if energy else 'no direct measurement'}",
        f"REL    {relationship_line}",
        f"DIFF   {'; '.join(changes)}",
    ]
    if accounting is not None:
        accounted = f"{accounting.accounted_total_wh}Wh" if accounting.accounted_total_wh is not None else "unknown"
        lines.append(f"ACCOUNT {accounted} topology={accounting.topology_status.value}")
    return "\n".join(lines)


def render_relationships(data: dict[str, object]) -> str:
    root = data.get("ietf-power-and-energy:energy-objects", {})
    objects = root.get("energy-object", []) if isinstance(root, dict) else []
    lines: list[str] = []
    for item in objects if isinstance(objects, list) else []:
        if not isinstance(item, dict):
            continue
        groups = item.get("relationship", [])
        if not isinstance(groups, list) or not groups:
            continue
        lines.append(str(item.get("id", "unknown")))
        for group in groups:
            if not isinstance(group, dict):
                continue
            identity = str(group.get("type", "unknown"))
            lines.append(f"  {identity.rsplit(':', 1)[-1].upper()}")
            peers = group.get("peer", [])
            for peer in peers if isinstance(peers, list) else []:
                if isinstance(peer, dict):
                    lines.append(f"    -> {peer.get('id', 'unknown')}")
    return "\n".join(lines) if lines else "(no Energy Object relationships)"


def render_interpretation(event: SimulatedEvent) -> str:
    title = USE_CASES_BY_SERIES[event.series].title
    lines = [f"{event.series.value} {title} / {event.sequence} {event.name}", event.explanation]
    if event.metadata:
        lines.append("Simulator/controller metadata:")
        lines.extend(f"  {key}: {value}" for key, value in event.metadata)
    else:
        lines.append("Simulator/controller metadata: none")
    return "\n".join(lines)


def render_json(data: dict[str, object]) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def render_relationship_diff(
    previous: SimulatedEvent | None,
    current: SimulatedEvent,
    visible_energy_object_ids: set[str] | frozenset[str] | None = None,
) -> str:
    if previous is None:
        return "No previous event is available for comparison."

    def relations(event: SimulatedEvent) -> set[tuple[str, str, str]]:
        return {
            (
                relationship.source_energy_object_id,
                relationship.relationship_type.value,
                relationship.peer_energy_object_id,
            )
            for relationship in event.relationships
            if visible_energy_object_ids is None or (
                relationship.source_energy_object_id in visible_energy_object_ids
                and relationship.peer_energy_object_id in visible_energy_object_ids
            )
        }

    before = relations(previous)
    after = relations(current)
    added = sorted(after - before)
    removed = sorted(before - after)
    lines = [f"Relationship diff: {previous.sequence} -> {current.sequence}"]
    lines.append("Added relationships:")
    lines.extend(f"  {source} {kind.upper()} -> {peer}" for source, kind, peer in added)
    if not added:
        lines.append("  (none)")
    lines.append("Removed relationships:")
    lines.extend(f"  {source} {kind.upper()} -> {peer}" for source, kind, peer in removed)
    if not removed:
        lines.append("  (none)")

    previous_states = dict(previous.component_states)
    current_states = dict(current.component_states)
    state_changes = [
        (object_id, previous_states.get(object_id), current_states.get(object_id))
        for object_id in sorted(previous_states.keys() | current_states.keys())
        if (visible_energy_object_ids is None or object_id in visible_energy_object_ids)
        if previous_states.get(object_id) != current_states.get(object_id)
    ]
    if state_changes:
        lines.append("Observed state changes:")
        lines.extend(
            f"  {object_id}: {before or '-'} -> {after or '-'}"
            for object_id, before, after in state_changes
        )
    return "\n".join(lines)


def filter_netconf_xml_to_energy_objects(
    xml: str,
    visible_energy_object_ids: set[str] | frozenset[str],
) -> str:
    netconf_ns = "urn:ietf:params:xml:ns:netconf:base:1.0"
    hardware_ns = "urn:ietf:params:xml:ns:yang:ietf-hardware"
    energy_ns = "urn:ietf:params:xml:ns:yang:ietf-power-and-energy"
    root = ET.fromstring(xml)
    data = root.find(f".//{{{netconf_ns}}}data")
    if data is None and root.tag == f"{{{netconf_ns}}}data":
        data = root
    if data is None:
        return xml

    energy_objects = data.find(f"{{{energy_ns}}}energy-objects")
    hardware = data.find(f"{{{hardware_ns}}}hardware")
    if energy_objects is None or hardware is None:
        return xml

    selected_component_names: set[str] = set()
    for energy_object in list(energy_objects.findall(f"{{{energy_ns}}}energy-object")):
        object_id = energy_object.findtext(f"{{{energy_ns}}}id")
        if object_id not in visible_energy_object_ids:
            energy_objects.remove(energy_object)
            continue

        component_name = energy_object.findtext(f"{{{energy_ns}}}source-component-id")
        if component_name:
            selected_component_names.add(component_name)

        for relationship in list(energy_object.findall(f"{{{energy_ns}}}relationship")):
            for peer in list(relationship.findall(f"{{{energy_ns}}}peer")):
                peer_id = peer.findtext(f"{{{energy_ns}}}id")
                if peer_id not in visible_energy_object_ids:
                    relationship.remove(peer)
            if not relationship.findall(f"{{{energy_ns}}}peer"):
                energy_object.remove(relationship)

    components = hardware.findall(f"{{{hardware_ns}}}component")
    components_by_name = {
        component.findtext(f"{{{hardware_ns}}}name"): component
        for component in components
        if component.findtext(f"{{{hardware_ns}}}name")
    }
    pending = list(selected_component_names)
    while pending:
        component = components_by_name.get(pending.pop())
        if component is None:
            continue
        parent = component.findtext(f"{{{hardware_ns}}}parent")
        if parent and parent not in selected_component_names:
            selected_component_names.add(parent)
            pending.append(parent)

    for component in list(components):
        component_name = component.findtext(f"{{{hardware_ns}}}name")
        if component_name not in selected_component_names:
            hardware.remove(component)
    return ET.tostring(root, encoding="unicode")


def fetch_netconf_xml(
    visible_energy_object_ids: set[str] | frozenset[str] | None = None,
) -> str:
    config_path = Path(__file__).resolve().parents[2] / "runtime" / "netconf" / "connection.env"
    config: dict[str, str] = {}
    if config_path.is_file():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator:
                config[key] = value

    host = os.environ.get("NETCONF_HOST") or config.get("NETCONF_HOST")
    port = int(os.environ.get("NETCONF_PORT", config.get("NETCONF_PORT", "830")))
    username = os.environ.get("NETCONF_USERNAME") or config.get("NETCONF_USERNAME")
    password = os.environ.get("NETCONF_PASSWORD") or config.get("NETCONF_PASSWORD")
    if not username or not password:
        raise RuntimeError("NETCONF XML view requires the local connection credentials")

    candidates = ["localhost"]
    if host and host not in candidates:
        candidates.append(host)
    selected_host = None
    for candidate in candidates:
        try:
            with socket.create_connection((candidate, port), timeout=1):
                selected_host = candidate
                break
        except OSError:
            continue
    if selected_host is None:
        raise RuntimeError(f"Netopeer2 is not reachable on port {port}")

    from ncclient import manager

    session = manager.connect_ssh(
        host=selected_host,
        port=port,
        username=username,
        password=password,
        hostkey_verify=False,
        allow_agent=False,
        look_for_keys=False,
        timeout=8,
        device_params={"name": "default"},
    )
    try:
        reply = session.get()
        if visible_energy_object_ids is None:
            return reply.xml
        return filter_netconf_xml_to_energy_objects(reply.xml, visible_energy_object_ids)
    finally:
        session.close_session()
