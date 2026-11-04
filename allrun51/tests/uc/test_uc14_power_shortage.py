from green.models import EventSeries, RelationshipType

from tests.uc.helpers import events_for, metadata
from green.topology import BACKUP_BATTERY_ID, GRID_SOURCE_ID


def test_power_shortage_switches_grid_battery_and_restores_service():
    events = events_for(EventSeries.UC_2_14)
    assert len(events) == 10
    assert [metadata(event)["power-source"] for event in events[:5]] == [
        "grid", "battery", "battery", "battery", "grid"
    ]
    relation_sources = [
        {r.source_energy_object_id for r in event.relationships if r.relationship_type is RelationshipType.POWERING}
        for event in events
    ]
    assert GRID_SOURCE_ID in relation_sources[0]
    assert BACKUP_BATTERY_ID in relation_sources[1]
    assert GRID_SOURCE_ID in relation_sources[4]
    assert metadata(events[3])["critical-service"] == "active"