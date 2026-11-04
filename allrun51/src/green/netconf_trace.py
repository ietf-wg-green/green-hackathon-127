import json
import os
import shutil
import threading
from collections.abc import Callable
from pathlib import Path
from textwrap import wrap

from green.energy_observability import build_observability_registry


_TRACE_WIDTH = 72


def _wrap_line(text: str, width: int = _TRACE_WIDTH) -> list[str]:
    indentation = text[: len(text) - len(text.lstrip())]
    content = text.strip()
    if not content:
        return [""]
    return wrap(
        content,
        width=max(1, width - len(indentation)),
        initial_indent=indentation,
        subsequent_indent=indentation,
        break_long_words=True,
        break_on_hyphens=False,
    )


def _hardware_inventory(data: object) -> list[str] | None:
    if not isinstance(data, dict):
        return None
    hardware = data.get("ietf-hardware:hardware")
    if not isinstance(hardware, dict):
        return None
    components = hardware.get("component")
    if not isinstance(components, list):
        return None

    rows = ["HARDWARE INVENTORY", f"{'Component':<22} {'Class':<16} UUID"]
    rows.append(f"{'-' * 22} {'-' * 16} --------")
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name", "unknown"))
        component_class = str(component.get("class", "unknown")).rsplit(":", 1)[-1]
        uuid = str(component.get("uuid", ""))
        uuid_suffix = f"...{uuid[-4:]}" if uuid else "-"
        rows.extend(_wrap_line(f"{name:<22} {component_class:<16} {uuid_suffix}"))
    return rows


def filter_yang_instance_to_energy_objects(
    data: dict[str, object],
    visible_energy_object_ids: set[str] | frozenset[str],
) -> dict[str, object]:
    energy_key = "ietf-power-and-energy:energy-objects"
    hardware_key = "ietf-hardware:hardware"
    energy_root = data.get(energy_key)
    hardware_root = data.get(hardware_key)
    if not isinstance(energy_root, dict) or not isinstance(hardware_root, dict):
        return data

    all_objects = energy_root.get("energy-object")
    all_components = hardware_root.get("component")
    if not isinstance(all_objects, list) or not isinstance(all_components, list):
        return data

    selected_objects = []
    selected_component_names: set[str] = set()
    for item in all_objects:
        if not isinstance(item, dict) or item.get("id") not in visible_energy_object_ids:
            continue
        selected = dict(item)
        component_name = item.get("source-component-id")
        if isinstance(component_name, str):
            selected_component_names.add(component_name)

        relationships = item.get("relationship")
        if isinstance(relationships, list):
            selected_relationships = []
            for relationship in relationships:
                if not isinstance(relationship, dict):
                    continue
                peers = relationship.get("peer")
                if not isinstance(peers, list):
                    continue
                selected_peers = [
                    peer for peer in peers
                    if isinstance(peer, dict) and peer.get("id") in visible_energy_object_ids
                ]
                if selected_peers:
                    selected_relationship = dict(relationship)
                    selected_relationship["peer"] = selected_peers
                    selected_relationships.append(selected_relationship)
            if selected_relationships:
                selected["relationship"] = selected_relationships
            else:
                selected.pop("relationship", None)
        selected_objects.append(selected)

    components_by_name = {
        item["name"]: item
        for item in all_components
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    pending = list(selected_component_names)
    while pending:
        component = components_by_name.get(pending.pop())
        if not component:
            continue
        parent = component.get("parent")
        if isinstance(parent, str) and parent not in selected_component_names:
            selected_component_names.add(parent)
            pending.append(parent)

    filtered_data = dict(data)
    filtered_energy_root = dict(energy_root)
    filtered_energy_root["energy-object"] = selected_objects
    filtered_data[energy_key] = filtered_energy_root
    filtered_hardware_root = dict(hardware_root)
    filtered_hardware_root["component"] = [
        item for name, item in components_by_name.items() if name in selected_component_names
    ]
    filtered_data[hardware_key] = filtered_hardware_root
    return filtered_data


def _energy_object_inventory(
    data: object,
    terminal_width: int | None = None,
) -> list[str] | None:
    if not isinstance(data, dict):
        return None
    energy_objects = data.get("ietf-power-and-energy:energy-objects")
    if not isinstance(energy_objects, dict):
        return None
    objects = energy_objects.get("energy-object")
    if not isinstance(objects, list):
        return None

    if terminal_width is None:
        terminal_width = shutil.get_terminal_size((80, 24)).columns
    compact = terminal_width < _TRACE_WIDTH
    column_widths = (20, 17, 7, 9, 14)

    def table_row(cells: list[str]) -> list[str]:
        wrapped_cells = [
            wrap(
                cell,
                width=width,
                break_long_words=True,
                break_on_hyphens=False,
            ) or [""]
            for cell, width in zip(cells, column_widths, strict=True)
        ]
        row_count = max(map(len, wrapped_cells))
        return [
            " ".join(
                (wrapped_cells[column][row] if row < len(wrapped_cells[column]) else "")
                .ljust(column_widths[column])
                for column in range(len(column_widths))
            ).rstrip()
            for row in range(row_count)
        ]

    rows = ["GREEN ENERGY OBJECTS"]
    if not compact:
        rows.extend(table_row(["Energy Object", "Source component", "Power", "State", "Relationships"]))
        rows.append("-" * _TRACE_WIDTH)
    observability = build_observability_registry()
    for item in objects:
        if not isinstance(item, dict):
            continue
        object_id = str(item.get("id", "unknown"))
        hardware_name = str(item.get("source-component-id", "-"))
        profile = observability.get(object_id)
        power_data = item.get("power")
        power_value = power_data.get("instantaneous-power") if isinstance(power_data, dict) else None
        power = profile.display_power(power_value) if profile else "UNKNOWN"
        state_data = item.get("power-state")
        state = state_data.get("oper") if isinstance(state_data, dict) else None
        state = str(state).rsplit(":", 1)[-1] if state is not None else None
        if state and state.startswith("power-state-"):
            state = state.removeprefix("power-state-")
        state = profile.display_state(state.upper() if state else None) if profile else "UNKNOWN"
        relationships: list[str] = []
        relationship_data = item.get("relationship")
        if isinstance(relationship_data, list):
            for relationship in relationship_data:
                if not isinstance(relationship, dict):
                    continue
                relationship_type = str(relationship.get("type", "unknown")).rsplit(":", 1)[-1]
                peers = relationship.get("peer")
                peer_count = len(peers) if isinstance(peers, list) else 0
                relationships.append(f"{relationship_type.upper()}({peer_count})")
        relationship_text = (
            profile.display_relationships(", ".join(relationships) if relationships else None)
            if profile
            else "UNKNOWN"
        )
        if compact:
            rows.extend(_wrap_line(f"{object_id} [{hardware_name}]", terminal_width))
            rows.extend(_wrap_line(f"  Power: {power} | State: {state}", terminal_width))
            rows.extend(_wrap_line(f"  Relationships: {relationship_text}", terminal_width))
        else:
            rows.extend(table_row([object_id, hardware_name, power, state, relationship_text]))
    return rows


def format_netconf_trace_entry(
    entry: str,
    visible_energy_object_ids: set[str] | frozenset[str] | None = None,
) -> str:
    lines = entry.splitlines()
    header = next(
        (line for line in lines if line.startswith("[") and "] " in line),
        "[unknown time] trace record",
    )
    timestamp, _, record_type = header[1:].partition("] ")
    context = next((line for line in lines if line.startswith("UC ")), "NETCONF GET")

    fields: dict[str, str] = {}
    for line in lines[1:]:
        key, separator, value = line.partition(":")
        if separator and key in {"operation", "module", "path", "request-xpath", "status"}:
            fields[key] = value.strip()

    payload = entry.partition("reply-data-json:")[2].strip()
    data: object | None = None
    try:
        data = json.loads(payload)
        formatted_payload = json.dumps(data, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        formatted_payload = payload or "(empty)"
    if isinstance(data, dict) and visible_energy_object_ids is not None:
        data = filter_yang_instance_to_energy_objects(data, visible_energy_object_ids)
        formatted_payload = json.dumps(data, indent=2, ensure_ascii=False)
    inventory = _hardware_inventory(data)
    energy_inventory = _energy_object_inventory(data)

    operation = fields.get("operation", record_type)
    status = fields.get("status", "unknown").upper()
    panel = ["NETCONF TRACE", *_wrap_line(context)]
    panel.extend(_wrap_line(f"{operation} | {status} | {timestamp}"))
    panel.extend(_wrap_line(f"Module: {fields.get('module', 'unknown')}"))
    panel.extend(_wrap_line(f"Path: {fields.get('path', 'unknown')}"))
    panel.extend(_wrap_line(f"Filter: {fields.get('request-xpath', '(not provided)')}"))
    if inventory is not None and energy_inventory is not None:
        panel.append("Reply: HARDWARE INVENTORY")
        for line in inventory[1:]:
            panel.extend(_wrap_line(line))
        panel.append("")
        for line in energy_inventory:
            panel.extend(_wrap_line(line))
    elif energy_inventory is not None:
        for line in energy_inventory:
            panel.extend(_wrap_line(line))
    elif inventory is not None:
        panel.append("Reply: HARDWARE INVENTORY")
        for line in inventory[1:]:
            panel.extend(_wrap_line(line))
    else:
        panel.append("Reply / JSON:")
        for line in formatted_payload.splitlines() or ["(empty)"]:
            panel.extend(_wrap_line(line))
    panel.append("-" * _TRACE_WIDTH)
    return "\n".join(panel)


class NetconfTraceTailer:
    def __init__(
        self,
        trace_path: Path,
        output_fn: Callable[[str], None],
        poll_interval: float = 0.1,
        *,
        visible_energy_object_ids: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.trace_path = trace_path
        self.output_fn = output_fn
        self.poll_interval = poll_interval
        self.visible_energy_object_ids = visible_energy_object_ids
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        try:
            self._start_offset = trace_path.stat().st_size
        except FileNotFoundError:
            self._start_offset = 0

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._tail, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stop_event.set()
        self._thread.join()
        self._thread = None

    def _tail(self) -> None:
        stream = None
        pending = ""
        offset = self._start_offset
        while not self._stop_event.is_set():
            if stream is None:
                try:
                    stream = self.trace_path.open("r", encoding="utf-8")
                    stream.seek(offset)
                except FileNotFoundError:
                    self._stop_event.wait(self.poll_interval)
                    continue
            pending, offset = self._read_entries(stream, pending, offset)
            self._stop_event.wait(self.poll_interval)

        if stream is None:
            try:
                stream = self.trace_path.open("r", encoding="utf-8")
                stream.seek(offset)
            except FileNotFoundError:
                return
        pending, _ = self._read_entries(stream, pending, offset)
        if pending.strip():
            self.output_fn(format_netconf_trace_entry(pending, self.visible_energy_object_ids))
        stream.close()

    def _read_entries(self, stream, pending: str, offset: int) -> tuple[str, int]:
        chunk = stream.read()
        offset = stream.tell()
        pending += chunk
        while "\n\n" in pending:
            entry, pending = pending.split("\n\n", 1)
            if entry.strip():
                self.output_fn(format_netconf_trace_entry(entry, self.visible_energy_object_ids))
        return pending, offset