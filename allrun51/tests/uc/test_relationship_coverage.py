from green.models import RELATIONSHIP_INVERSES, RelationshipType
from green.simulator import generate_events
from green.topology import demo_energy_objects


FAMILY_COVERAGE = {
    (RelationshipType.METERING, RelationshipType.METERED_BY): {
        "UC 2.5", "UC 2.9", "UC 2.13",
    },
    (RelationshipType.AGGREGATING, RelationshipType.AGGREGATED_BY): {
        "UC 2.6", "UC 2.11", "UC 2.12",
    },
    (RelationshipType.POWERING, RelationshipType.POWERED_BY): {
        "UC 2.5", "UC 2.9", "UC 2.14",
    },
    (RelationshipType.ENABLING, RelationshipType.ENABLED_BY): {
        "UC 2.9", "UC 2.10", "UC 2.16",
    },
}


def test_every_relationship_family_has_three_ucs_and_four_events_per_uc():
    events = generate_events()
    for family, use_cases in FAMILY_COVERAGE.items():
        assert len(use_cases) >= 3
        for use_case in use_cases:
            selected = [event for event in events if event.series.value == use_case]
            covered = [
                event for event in selected
                if any(rel.relationship_type in family for rel in event.relationships)
                or "relationship-change" in dict(event.metadata)
            ]
            assert len(covered) >= 4, (family, use_case, [event.sequence for event in covered])


def test_relationship_families_are_paired_directionally_without_derivation():
    events = generate_events()
    for event in events:
        keys = {
            (rel.source_energy_object_id, rel.relationship_type, rel.peer_energy_object_id)
            for rel in event.relationships
        }
        for source, kind, peer in keys:
            inverse = (peer, RELATIONSHIP_INVERSES[kind], source)
            assert inverse in keys


def test_relationship_peer_ids_resolve_and_never_self_reference():
    known = {item.energy_object_id for item in demo_energy_objects()}
    for event in generate_events():
        seen = set()
        for rel in event.relationships:
            key = (rel.source_energy_object_id, rel.relationship_type, rel.peer_energy_object_id)
            assert rel.source_energy_object_id != rel.peer_energy_object_id
            assert rel.source_energy_object_id in known
            assert rel.peer_energy_object_id in known
            assert key not in seen
            seen.add(key)


def test_relationship_families_are_not_conflated_with_traffic_actions():
    events = generate_events()
    uc06_aggregation = [
        rel for event in events if event.series.value == "UC 2.6" for rel in event.relationships
        if rel.relationship_type is RelationshipType.AGGREGATING
    ]
    assert uc06_aggregation
    assert all("domain-energy-aggregator" in rel.source_energy_object_id for rel in uc06_aggregation)
    assert all("traffic-relocated-to" not in dict(event.metadata).values() for event in events)