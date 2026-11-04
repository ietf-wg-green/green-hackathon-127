from green.models import ComponentState, EventSeries, RelationshipType
from green.topology import LINECARD_1_ID, TRANSPORT_MODULE_ID

from tests.uc.helpers import events_for, metadata


def test_cross_layer_sleep_coordinates_ip_and_transport_dependencies():
    events = events_for(EventSeries.UC_2_16)
    assert len(events) == 10
    assert all(RelationshipType.ENABLING in {r.relationship_type for r in event.relationships} for event in events)
    assert dict(events[1].component_states)[LINECARD_1_ID] is ComponentState.LOW_POWER
    assert dict(events[2].component_states)[TRANSPORT_MODULE_ID] is ComponentState.LOW_POWER
    assert metadata(events[2])["coordination"] == "overlay-underlay"
    assert dict(events[-1].component_states)[TRANSPORT_MODULE_ID] is ComponentState.ACTIVE