from green.models import ComponentState, EventSeries
from green.topology import AI_NODE_2_ID

from tests.uc.helpers import events_for, metadata


def test_ai_training_events_cover_east_west_scheduling_transfer_and_nodes():
    events = events_for(EventSeries.UC_2_15)
    assert len(events) == 8
    assert metadata(events[0])["east-west-traffic-gb"] == "800"
    assert metadata(events[1])["schedule-window"] == "lower-energy-period"
    assert metadata(events[2])["compression"] == "enabled"
    assert metadata(events[2])["data-placement"] == "near-compute"
    assert dict(events[3].component_states)[AI_NODE_2_ID] is ComponentState.LOW_POWER