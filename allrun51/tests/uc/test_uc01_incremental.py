from green.models import EventSeries
from green.topology import LINECARD_1_ID, LINECARD_2_ID

from tests.uc.helpers import events_for, metadata


def test_incremental_baseline_component_device_and_network_stages():
    events = events_for(EventSeries.UC_2_1)
    assert len(events) == 8
    assert [event.sequence for event in events[:4]] == ["U1-0", "U1-1", "U1-2", "U1-3"]
    assert not events[0].measurements and not events[0].power_measurements
    assert {item.energy_object_id for item in events[1].power_measurements} == {LINECARD_1_ID}
    assert LINECARD_2_ID not in {item.energy_object_id for item in events[1].power_measurements}
    assert metadata(events[2])["observed-power-w"] == "420"
    assert metadata(events[3])["network-stage"] == "NETWORK_LEVEL_GREEN"