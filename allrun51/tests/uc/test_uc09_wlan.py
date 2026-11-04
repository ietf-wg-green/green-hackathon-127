from green.models import ComponentState, EventSeries, RelationshipType
from green.topology import AP_1_ID, AP_RADIO_5_ID, POE_PORT_AP1_ID

from tests.uc.helpers import events_for, metadata


def test_wlan_preserves_active_low_power_hibernate_poe_off_and_wake_modes():
    events = events_for(EventSeries.UC_2_9)
    assert len(events) == 10
    assert [event.name for event in events[:5]] == [
        "AP_ACTIVE", "AP_LOW_POWER", "AP_HIBERNATING", "POE_POWER_OFF", "AP_REACTIVATED"
    ]
    assert dict(events[1].component_states)[AP_RADIO_5_ID] is ComponentState.OFF
    assert dict(events[2].component_states)[AP_1_ID] is ComponentState.HIBERNATING
    assert metadata(events[2])["standard-yang-power-state"] == "not-defined"
    assert dict(events[3].component_states)[POE_PORT_AP1_ID] is ComponentState.OFF
    assert metadata(events[3])["recovery-delay"] == "minutes"
    required = {RelationshipType.METERING, RelationshipType.POWERING, RelationshipType.ENABLING}
    assert all(required <= {r.relationship_type for r in event.relationships} for event in events)