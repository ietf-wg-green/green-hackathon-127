from green.accounting import AccountingEngine
from green.models import EventSeries, TopologyStatus
from green.topology import build_demo_topology

from tests.uc.helpers import events_for


def test_uc13_accounting_remains_topology_driven():
    events = events_for(EventSeries.UC_2_13)
    results = []
    for event in events:
        topology, boundary = build_demo_topology(relationships=event.relationships)
        results.append(AccountingEngine().compute(
            boundary, event.measurements, topology, series=event.series.value,
            event_sequence=event.sequence, event_name=event.name,
        ))
    anchor_results = results[:4]
    assert [result.naive_total_wh for result in anchor_results] == [600, 600, 670, 610]
    assert [result.accounted_total_wh for result in anchor_results] == [None, 300, 340, None]
    assert anchor_results[0].topology_status is TopologyStatus.INCOMPLETE
    assert anchor_results[1].topology_status is TopologyStatus.COMPLETE
    assert anchor_results[3].topology_status is TopologyStatus.INCOMPLETE