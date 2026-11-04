from green.models import EventSeries

from tests.uc.helpers import events_for, metadata


def test_video_delivery_optimization_uses_documented_choices():
    events = events_for(EventSeries.UC_2_8)
    assert [metadata(event).get("delivery-strategy") for event in events[:2]] == [
        "unicast", "multicast-demonstration"
    ]
    assert metadata(events[1])["standardized-control-protocol"] == "not-claimed"
    assert metadata(events[2])["cache-placement"] == "near-users"
    assert metadata(events[3])["backbone-traffic"] == "reduced"