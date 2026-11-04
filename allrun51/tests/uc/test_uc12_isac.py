from green.models import ComponentState, EventSeries
from green.topology import RADAR_SENSOR_ID

from tests.uc.helpers import events_for, metadata


def test_isac_adapts_optional_sensing_but_preserves_critical_functions():
    events = events_for(EventSeries.UC_2_12)
    assert len(events) == 10
    assert dict(events[2].component_states)[RADAR_SENSOR_ID] is ComponentState.LOW_POWER
    assert metadata(events[2])["critical-sensing"] == "active"
    assert metadata(events[3])["critical-functions"] == "preserved"