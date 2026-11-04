import threading
import xml.etree.ElementTree as ET

from green.simulator import EventSimulator
from green.yang_adapter import to_yang_instance
from green.topology import demo_energy_objects
from green.netconf_trace import NetconfTraceTailer


HARDWARE_NS = "urn:ietf:params:xml:ns:yang:ietf-hardware"
GREEN_NS = "urn:ietf:params:xml:ns:yang:ietf-power-and-energy"


def event_at(sequence: str):
    simulator = EventSimulator()
    while (event := simulator.next_event()) is not None:
        if event.sequence == sequence:
            return event
    raise AssertionError(f"missing simulator event: {sequence}")


def publish(event) -> None:
    from green.netconf_bridge import write_operational_snapshot

    write_operational_snapshot(event)


def test_netconf_get_is_written_to_provider_trace(netconf_manager) -> None:
    from green.netconf_bridge import set_netconf_trace_enabled

    trace_path = set_netconf_trace_enabled(True)
    formatted_records: list[str] = []
    record_received = threading.Event()

    def capture_record(record: str) -> None:
        formatted_records.append(record)
        if "<get> | OK" in record:
            record_received.set()

    tailer = NetconfTraceTailer(trace_path, capture_record)
    tailer.start()
    try:
        publish(event_at("U13-1"))
        get_energy_objects(netconf_manager)
        assert record_received.wait(timeout=5), "live trace did not receive the NETCONF GET"
        trace = trace_path.read_text(encoding="utf-8")
    finally:
        set_netconf_trace_enabled(False)
        tailer.stop()

    assert "operation: <get>" in trace
    assert "module: ietf-power-and-energy" in trace
    assert "request-xpath:" in trace
    assert "------------------------------------------------------------------------" in trace
    assert "UC 2.13 - Double Accounting Open issue | U13-1 TOPOLOGY_DISCOVERED" in trace
    get_record = next(record for record in formatted_records if "<get> | OK" in record)
    assert "GREEN ENERGY OBJECTS" in get_record
    assert "eo-upstream-meter" in get_record
    assert "UC 2.13 - Double Accounting Open issue | U13-1 TOPOLOGY_DISCOVERED" in get_record
    assert "upstream-meter" in get_record
    assert "METERING(2)" in get_record


def test_hardware_get_is_prettified_as_inventory(netconf_manager) -> None:
    from green.netconf_bridge import set_netconf_trace_enabled

    trace_path = set_netconf_trace_enabled(True)
    records: list[str] = []
    inventory_received = threading.Event()

    def capture_record(record: str) -> None:
        records.append(record)
        if "Reply: HARDWARE INVENTORY" in record:
            inventory_received.set()

    tailer = NetconfTraceTailer(trace_path, capture_record)
    tailer.start()
    try:
        publish(event_at("U13-1"))
        get_hardware(netconf_manager)
        assert inventory_received.wait(timeout=5), "hardware GET did not render an inventory"
    finally:
        set_netconf_trace_enabled(False)
        tailer.stop()

    inventory = next(record for record in records if "Reply: HARDWARE INVENTORY" in record)
    assert "Component" in inventory and "Class" in inventory and "UUID" in inventory
    assert "upstream-meter" in inventory and "energy-object" in inventory
    assert "...0001" in inventory
    assert all(len(line) <= 72 for line in inventory.splitlines())


def get_hardware(netconf_manager):
    reply = netconf_manager.get(
        filter=("subtree", f'<hardware xmlns="{HARDWARE_NS}"/>')
    )
    return ET.fromstring(reply.data_xml)


def get_energy_objects(netconf_manager):
    reply = netconf_manager.get(
        filter=("subtree", f'<energy-objects xmlns="{GREEN_NS}"/>')
    )
    root = ET.fromstring(reply.data_xml)
    return {
        item.find(f"{{{GREEN_NS}}}id").text: item
        for item in root.findall(f".//{{{GREEN_NS}}}energy-object")
    }


def leaf(item: ET.Element, container: str, name: str) -> str | None:
    node = item.find(f"{{{GREEN_NS}}}{container}/{{{GREEN_NS}}}{name}")
    return node.text if node is not None else None


def power_state(item: ET.Element) -> str | None:
    node = item.find(f"{{{GREEN_NS}}}power-state/{{{GREEN_NS}}}oper")
    return node.text.rsplit(":", 1)[-1] if node is not None else None


def test_netconf_connection(netconf_manager) -> None:
    assert netconf_manager.session_id
    assert any(
        capability in netconf_manager.server_capabilities
        for capability in (
            "urn:ietf:params:netconf:base:1.0",
            "urn:ietf:params:netconf:base:1.1",
        )
    )


def test_rfc8348_hardware_get_returns_all_required_components(netconf_manager) -> None:
    publish(event_at("U13-1"))
    root = get_hardware(netconf_manager)
    names = {
        name.text
        for name in root.findall(f".//{{{HARDWARE_NS}}}component/{{{HARDWARE_NS}}}name")
    }

    assert {
        "upstream-meter",
        "server-A",
        "server-B",
        "router-A",
        "router-B",
        "linecard-1",
        "linecard-2",
        "switchable-port",
    } <= names


def test_green_energy_objects_get_correlates_hardware_and_relationships(netconf_manager) -> None:
    publish(event_at("U13-1"))
    objects = get_energy_objects(netconf_manager)

    assert set(objects) == {item.energy_object_id for item in demo_energy_objects()}
    upstream = objects["eo-upstream-meter"]
    source_component = upstream.find(f"{{{GREEN_NS}}}source-component-id")
    assert source_component is not None
    assert source_component.text == "upstream-meter"

    relations = upstream.findall(f"{{{GREEN_NS}}}relationship")
    assert len(relations) == 1
    relationship_type = relations[0].find(f"{{{GREEN_NS}}}type")
    assert relationship_type is not None
    assert relationship_type.text.rsplit(":", 1)[-1] == "metering"
    peer_ids = {
        peer.find(f"{{{GREEN_NS}}}id").text
        for peer in relations[0].findall(f"{{{GREEN_NS}}}peer")
    }
    assert peer_ids == {"eo-server-a", "eo-server-b"}


def test_uc213_topology_changes_are_visible_through_get(netconf_manager) -> None:
    publish(event_at("U13-0"))
    raw_objects = get_energy_objects(netconf_manager)
    assert not raw_objects["eo-upstream-meter"].findall(f"{{{GREEN_NS}}}relationship")

    publish(event_at("U13-1"))
    discovered_objects = get_energy_objects(netconf_manager)
    assert discovered_objects["eo-upstream-meter"].findall(f"{{{GREEN_NS}}}relationship")

    publish(event_at("U13-3"))
    incomplete_objects = get_energy_objects(netconf_manager)
    peers = incomplete_objects["eo-upstream-meter"].findall(
        f"{{{GREEN_NS}}}relationship/{{{GREEN_NS}}}peer/{{{GREEN_NS}}}id"
    )
    assert [peer.text for peer in peers] == ["eo-server-a"]


def test_uc210_live_energy_and_sleep_wake_are_visible(netconf_manager) -> None:
    publish(event_at("U10-0"))
    objects = get_energy_objects(netconf_manager)
    assert leaf(objects["eo-router-a"], "power", "instantaneous-power") == "500000"
    assert leaf(objects["eo-router-b"], "power", "instantaneous-power") == "480000"
    assert "energy" not in objects["eo-upstream-meter"]

    publish(event_at("U10-1"))
    objects = get_energy_objects(netconf_manager)
    assert leaf(objects["eo-router-a"], "power", "instantaneous-power") == "340000"
    assert leaf(objects["eo-router-b"], "power", "instantaneous-power") == "330000"

    publish(event_at("U10-2"))
    objects = get_energy_objects(netconf_manager)
    assert power_state(objects["eo-router-a-linecard-1"]) == "power-state-sleep"

    publish(event_at("U10-3"))
    objects = get_energy_objects(netconf_manager)
    assert power_state(objects["eo-router-a-linecard-1"]) == "power-state-on"
    assert leaf(objects["eo-router-a"], "power", "instantaneous-power") == "460000"


def test_uc21_partial_deployment_exposes_only_measured_component(netconf_manager) -> None:
    event = event_at("U1-1")
    publish(event)
    objects = get_energy_objects(netconf_manager)
    linecard = objects["eo-router-a-linecard-1"]
    assert leaf(linecard, "power", "instantaneous-power") == "120000"

    legacy_linecard = objects["eo-router-a-linecard-2"]
    assert leaf(legacy_linecard, "power", "instantaneous-power") is None
    assert leaf(legacy_linecard, "energy", "total-energy-consumed") is None


def test_uc21_device_and_mixed_network_migration_are_visible(netconf_manager) -> None:
    publish(event_at("U1-2"))
    device_objects = get_energy_objects(netconf_manager)
    assert leaf(device_objects["eo-router-a"], "power", "instantaneous-power") == "420000"

    publish(event_at("U1-3"))
    mixed_objects = get_energy_objects(netconf_manager)
    assert leaf(mixed_objects["eo-router-a"], "power", "instantaneous-power") == "420000"
    assert leaf(mixed_objects["eo-router-b"], "power", "instantaneous-power") == "380000"


def test_uc214_grid_failure_critical_service_and_recovery_are_read_only(netconf_manager) -> None:
    publish(event_at("U14-1"))
    failed_grid_objects = get_energy_objects(netconf_manager)
    assert power_state(failed_grid_objects["eo-router-a"]) == "power-state-on"

    publish(event_at("U14-2"))
    battery_objects = get_energy_objects(netconf_manager)
    assert power_state(battery_objects["eo-router-b"]) == "power-state-sleep"
    assert power_state(battery_objects["eo-router-b-switchable-port"]) == "power-state-off"

    publish(event_at("U14-3"))
    critical_objects = get_energy_objects(netconf_manager)
    assert power_state(critical_objects["eo-router-a"]) == "power-state-on"
    assert power_state(critical_objects["eo-router-b"]) == "power-state-sleep"
    assert power_state(critical_objects["eo-router-b-switchable-port"]) == "power-state-off"
    assert leaf(critical_objects["eo-router-a"], "power", "instantaneous-power") == "380000"
    assert leaf(critical_objects["eo-router-b"], "power", "instantaneous-power") == "200000"

    publish(event_at("U14-4"))
    restored_objects = get_energy_objects(netconf_manager)
    assert power_state(restored_objects["eo-router-a"]) == "power-state-on"
    assert power_state(restored_objects["eo-router-b"]) == "power-state-on"