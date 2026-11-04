from pathlib import Path

from green.canonical_docs import write_canonical_documents
from green.markdown_tables import align_markdown_tables


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_architecture_documents_cover_the_canonical_network() -> None:
    paths = write_canonical_documents()
    assert {path.name for path in paths} == {
        "canonical_network.md",
        "device_archetypes.md",
        "uc_topology_matrix.md",
        "controller_identity_model.md",
        "relationship_behavior_classes.md",
        "future_capability_profile_model.md",
        "energy_object_observability.md",
    }
    for path in paths:
        assert path.is_relative_to(PROJECT_ROOT / "docs")
        assert path.is_file()

    topology = (PROJECT_ROOT / "docs" / "canonical_network.md").read_text(encoding="utf-8")
    assert "DEMO-NETWORK-1" in topology
    assert all(f"T{index}-" in topology for index in range(1, 7))
    assert all(f"T{index} " in topology for index in range(1, 7))
    matrix = (PROJECT_ROOT / "docs" / "uc_topology_matrix.md").read_text(encoding="utf-8")
    assert "UC 2.16" in matrix and "UC 2.1" in matrix
    identities = (PROJECT_ROOT / "docs" / "controller_identity_model.md").read_text(encoding="utf-8")
    assert "(device_id, hardware_component_name)" in identities
    assert "(device_id, energy_object_id)" in identities
    classes = (PROJECT_ROOT / "docs" / "relationship_behavior_classes.md").read_text(encoding="utf-8")
    assert "stable-structural" in classes
    assert "physical-dynamic" in classes
    assert "knowledge-observability" in classes
    observability = (PROJECT_ROOT / "docs" / "energy_object_observability.md").read_text(encoding="utf-8")
    assert observability.count("| `eo-") == 44
    assert "UNKNOWN" in observability and "N/A" in observability


def test_readme_contains_topology_short_labels_and_internals_flow() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    for label in (
        "T1 | CORE | Fixed Network",
        "T2 | AIR | WLAN / PoE",
        "T3 | POWER | Power Infrastructure",
        "T4 | BACKHAUL | Wireless Transport",
        "T5 | EDGE | Edge / Compute",
        "T6 | CITY | ISAC / Smart City",
    ):
        assert label in readme
    stages = (
        "device archetypes",
        "device instances",
        "canonical topology",
        "UC overlays",
        "YANG adapter",
        "Sysrepo / Netopeer2",
        "NETCONF",
    )
    assert [readme.index(stage) for stage in stages] == sorted(readme.index(stage) for stage in stages)


def test_generated_markdown_tables_are_column_aligned() -> None:
    write_canonical_documents()
    for path in (PROJECT_ROOT / "docs").rglob("*.md"):
        document = path.read_text(encoding="utf-8")
        assert align_markdown_tables(document) == document, path
        table_rows = [
            line for line in document.splitlines()
            if line.startswith("|") and line.endswith("|")
        ]
        assert all(len(line) <= 160 for line in table_rows), path