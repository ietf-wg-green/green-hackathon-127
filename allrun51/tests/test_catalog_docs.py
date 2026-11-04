from collections import Counter
import re

from green.catalog_docs import render_event_catalog, render_relationship_coverage
from green.catalog import EVENT_CATALOG


EXPECTED_EVENT_COUNTS = {
    "UC 2.1": 8, "UC 2.2": 10, "UC 2.5": 8, "UC 2.6": 8,
    "UC 2.7": 8, "UC 2.8": 8, "UC 2.9": 10, "UC 2.10": 8,
    "UC 2.11": 8, "UC 2.12": 10, "UC 2.13": 8, "UC 2.14": 10,
    "UC 2.15": 8, "UC 2.16": 10,
}


def test_generated_event_catalog_has_122_unique_described_events() -> None:
    document = render_event_catalog()
    rows = [line for line in document.splitlines() if re.match(r"\| UC 2\.\d+ \|", line)]
    ids = []
    counts: Counter[str] = Counter()
    for row in rows:
        cells = [cell.strip() for cell in row.split("|")[1:-1]]
        ids.append(cells[1])
        counts[cells[0]] += 1
        assert cells[2]
    assert len(rows) == 122
    assert len(set(ids)) == 122
    assert counts == EXPECTED_EVENT_COUNTS
    assert "14 use cases, 122 deterministic events" in document
    for event in EVENT_CATALOG:
        assert event.sequence in ids
        assert event.explanation in document
        assert len(event.explanation.split()) < 20


def test_relationship_coverage_doc_lists_four_events_for_each_required_uc() -> None:
    document = render_relationship_coverage()
    rows = [line for line in document.splitlines() if line.startswith("| ") and "UC 2." in line]
    assert len(rows) == 12
    for row in rows:
        cells = [cell.strip() for cell in row.split("|")[1:-1]]
        event_ids = [item.strip() for item in cells[2].split(",") if item.strip()]
        assert len(event_ids) >= 4, (cells[0], cells[1], event_ids)