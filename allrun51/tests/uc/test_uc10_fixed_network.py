from green.models import ComponentState, EventSeries, RelationshipType
from green.topology import LINECARD_1_ID, ROUTER_A_ID, ROUTER_B_ID

from tests.uc.helpers import events_for


def test_fixed_network_router_power_and_linecard_states_are_preserved():
    events = events_for(EventSeries.UC_2_10)
    assert len(events) == 8
    assert [event.name for event in events[:4]] == [
        "TRAFFIC_HIGH", "TRAFFIC_LOW", "COMPONENT_SLEEP", "TRAFFIC_BURST"
    ]
    assert all(not event.measurements for event in events)
    expected_router_power_w = [
        {ROUTER_A_ID: 500, ROUTER_B_ID: 480},
        {ROUTER_A_ID: 340, ROUTER_B_ID: 330},
        {ROUTER_A_ID: 220, ROUTER_B_ID: 390},
        {ROUTER_A_ID: 460, ROUTER_B_ID: 470},
        {ROUTER_A_ID: 490, ROUTER_B_ID: 470},
        {ROUTER_A_ID: 280, ROUTER_B_ID: 420},
        {ROUTER_A_ID: 360, ROUTER_B_ID: 440},
        {ROUTER_A_ID: 470, ROUTER_B_ID: 475},
    ]
    assert [
        {item.energy_object_id: item.instantaneous_power_w for item in event.power_measurements}
        for event in events
    ] == expected_router_power_w
    assert dict(events[2].component_states)[LINECARD_1_ID] is ComponentState.LOW_POWER
    assert dict(events[3].component_states)[LINECARD_1_ID] is ComponentState.ACTIVE
    assert dict(events[5].component_states)[LINECARD_1_ID] is ComponentState.LOW_POWER
    assert dict(events[6].component_states)[LINECARD_1_ID] is ComponentState.ACTIVE
    assert all(RelationshipType.ENABLING in {r.relationship_type for r in event.relationships} for event in events)