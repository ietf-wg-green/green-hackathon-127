from green.models import ComponentState, EventSeries
from green.topology import LINECARD_1_ID, ROUTER_A_ID, ROUTER_B_ID

from tests.uc.helpers import events_for, metadata


def test_traffic_valleys_relocation_sleep_and_recovery():
    events = events_for(EventSeries.UC_2_2)
    assert len(events) == 10
    assert [event.name for event in events[:5]] == [
        "TRAFFIC_PEAK", "TRAFFIC_VALLEY", "TRAFFIC_RELOCATED",
        "COMPONENTS_SLEEPING", "TRAFFIC_RECOVERY",
    ]
    relocated = metadata(events[2])
    assert relocated["traffic-action"] == "relocated-to-router-B"
    assert dict(events[3].component_states)[LINECARD_1_ID] is ComponentState.LOW_POWER
    assert metadata(events[4])["service-continuity"] == "maintained"
    assert {item.energy_object_id for item in events[2].power_measurements} == {ROUTER_A_ID, ROUTER_B_ID}