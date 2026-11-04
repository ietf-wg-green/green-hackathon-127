from green.models import EventSeries, RelationshipType

from tests.uc.helpers import events_for, metadata


def test_cross_domain_mapping_guard_and_composition_are_explicit():
    events = events_for(EventSeries.UC_2_6)
    assert len(events) == 8
    assert [event.name for event in events[:4]] == [
        "DOMAIN_METRICS_AVAILABLE", "METRICS_MAPPED",
        "DOUBLE_COUNTING_GUARD_APPLIED", "END_TO_END_METRIC_COMPOSED",
    ]
    assert all(RelationshipType.AGGREGATING in {r.relationship_type for r in event.relationships} for event in events)
    assert metadata(events[1])["mapping-status"] == "normalized-to-Wh"
    assert metadata(events[2])["accounting-guard"] == "domain-boundary"
    assert metadata(events[3])["composition-status"] == "complete"