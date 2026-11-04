from green.models import EventSeries, RelationshipType
from green.topology import ROUTER_A_ID, ROUTER_B_ID, ROUTER_C_ID

from tests.uc.helpers import events_for, metadata


def test_network_management_collects_and_aggregates_observability():
    events = events_for(EventSeries.UC_2_11)
    assert len(events) == 8
    assert [event.name for event in events[:4]] == [
        "INVENTORY_DISCOVERED", "REALTIME_TELEMETRY_COLLECTED",
        "CAPABILITIES_AND_LEGACY_CLASSIFIED", "NETWORK_ENERGY_TREND_AGGREGATED",
    ]
    assert {item.energy_object_id for item in events[1].power_measurements} == {
        ROUTER_A_ID, ROUTER_B_ID, ROUTER_C_ID
    }
    assert metadata(events[2])["unsupported-capability"] == "unknown"
    assert all(RelationshipType.AGGREGATING in {r.relationship_type for r in event.relationships} for event in events)