from green.models import EventSeries, RelationshipType
from green.topology import LEGACY_DEVICE_ID, PDU_OUTLET_ID

from tests.uc.helpers import events_for, metadata


def test_pdu_measurement_never_fabricates_target_telemetry():
    events = events_for(EventSeries.UC_2_5)
    assert len(events) == 8
    for event in events:
        assert metadata(event)["target-direct-measurement"] == "unknown"
        assert LEGACY_DEVICE_ID not in {item.energy_object_id for item in event.power_measurements}
        assert PDU_OUTLET_ID in {item.energy_object_id for item in event.power_measurements}
        assert {item.relationship_type for item in event.relationships} == {
            RelationshipType.METERING, RelationshipType.METERED_BY,
            RelationshipType.POWERING, RelationshipType.POWERED_BY,
        }