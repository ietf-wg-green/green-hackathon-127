from green.models import ComponentState, EventSeries
from green.topology import WIRELESS_LINK_ID

from tests.uc.helpers import events_for


def test_wireless_link_power_tracks_traffic_and_recovers():
    events = events_for(EventSeries.UC_2_7)
    powers = [event.power_measurements[0].instantaneous_power_w for event in events]
    assert powers[0] > powers[2] < powers[3]
    assert dict(events[2].component_states)[WIRELESS_LINK_ID] is ComponentState.LOW_POWER
    assert dict(events[3].component_states)[WIRELESS_LINK_ID] is ComponentState.ACTIVE