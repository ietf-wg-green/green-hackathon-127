import json
import xml.etree.ElementTree as ET

from green.models import RelationshipType
from green.netconf_bridge import write_operational_snapshot
from green.simulator import generate_events
from green.topology import demo_energy_objects
from green.views import event_to_yang, render_relationships


GREEN_NS = "urn:ietf:params:xml:ns:yang:ietf-power-and-energy"
HARDWARE_NS = "urn:ietf:params:xml:ns:yang:ietf-hardware"
EXPECTED_EVENT_COUNTS = {
    "UC 2.1": 8, "UC 2.2": 10, "UC 2.5": 8, "UC 2.6": 8,
    "UC 2.7": 8, "UC 2.8": 8, "UC 2.9": 10, "UC 2.10": 8,
    "UC 2.11": 8, "UC 2.12": 10, "UC 2.13": 8, "UC 2.14": 10,
    "UC 2.15": 8, "UC 2.16": 10,
}


def test_each_group_a_use_case_is_retrievable_over_netconf(netconf_manager):
    events_by_series = {}
    for event in generate_events():
        events_by_series.setdefault(event.series, []).append(event)

    assert len(events_by_series) == 14
    for series_events in events_by_series.values():
        assert len(series_events) == EXPECTED_EVENT_COUNTS[series_events[0].series.value]
        write_operational_snapshot(series_events[0])
        reply = netconf_manager.get()
        root = ET.fromstring(reply.data_xml)
        assert root.find(f".//{{{GREEN_NS}}}energy-object") is not None
        assert root.find(f".//{{{HARDWARE_NS}}}component") is not None


def test_hardware_parent_and_source_component_mapping_are_visible(netconf_manager):
    event = next(event for event in generate_events() if event.sequence == "U1-1")
    write_operational_snapshot(event)
    reply = netconf_manager.get(filter=("subtree", f'<hardware xmlns="{HARDWARE_NS}"/>'))
    root = ET.fromstring(reply.data_xml)
    components = {
        item.find(f"{{{HARDWARE_NS}}}name").text: item
        for item in root.findall(f".//{{{HARDWARE_NS}}}component")
    }
    assert components["linecard-1"].find(f"{{{HARDWARE_NS}}}parent").text == "router-A"

    energy_reply = netconf_manager.get(filter=("subtree", f'<energy-objects xmlns="{GREEN_NS}"/>'))
    energy_root = ET.fromstring(energy_reply.data_xml)
    linecard = next(
        item for item in energy_root.findall(f".//{{{GREEN_NS}}}energy-object")
        if item.find(f"{{{GREEN_NS}}}id").text == "eo-router-a-linecard-1"
    )
    assert linecard.find(f"{{{GREEN_NS}}}source-component-id").text == "linecard-1"


def test_all_eight_directional_identities_are_raw_netconf_data(netconf_manager):
    sequences = {"U5-0", "U6-0", "U9-0", "U10-0", "U13-1", "U14-0", "U16-0"}
    identities: set[str] = set()
    for event in generate_events():
        if event.sequence not in sequences:
            continue
        write_operational_snapshot(event)
        reply = netconf_manager.get(
            filter=("subtree", f'<energy-objects xmlns="{GREEN_NS}"/>')
        )
        root = ET.fromstring(reply.data_xml)
        identities.update(
            item.text.rsplit(":", 1)[-1]
            for item in root.findall(f".//{{{GREEN_NS}}}relationship/{{{GREEN_NS}}}type")
        )
    assert identities == {kind.value for kind in RelationshipType}


def test_xml_json_and_relationship_summary_remain_parseable(netconf_manager):
    event = next(event for event in generate_events() if event.sequence == "U9-0")
    aggregate_event = next(event for event in generate_events() if event.sequence == "U6-0")
    write_operational_snapshot(event)
    reply = netconf_manager.get()
    root = ET.fromstring(reply.xml)
    assert root.tag.endswith("rpc-reply")

    json_data = event_to_yang(event, demo_energy_objects())
    assert json.loads(json.dumps(json_data)) == json_data
    summary = render_relationships(json_data)
    aggregate_data = event_to_yang(aggregate_event, demo_energy_objects())
    summary += "\n" + render_relationships(aggregate_data)
    assert "METERING" in summary
    assert "METERED-BY" in summary
    assert "POWERING" in summary
    assert "POWERED-BY" in summary
    assert "ENABLING" in summary
    assert "ENABLED-BY" in summary
