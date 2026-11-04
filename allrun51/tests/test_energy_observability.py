import json

from green.energy_observability import (
    ObservabilityClass,
    build_observability_registry,
)
from green.topology import (
    LINECARD_2_ID,
    NON_CRITICAL_PORT_ID,
    UPSTREAM_METER_ID,
    demo_energy_objects,
)
from green.yang_adapter import to_yang_instance


def test_every_energy_object_has_one_evidence_based_observability_class() -> None:
    objects = demo_energy_objects()
    registry = build_observability_registry(objects)

    assert set(registry) == {item.energy_object_id for item in objects}
    assert {item.observability_class for item in registry.values()} == set(ObservabilityClass)
    assert registry[NON_CRITICAL_PORT_ID].observability_class is ObservabilityClass.STATE_ONLY
    assert registry[UPSTREAM_METER_ID].observability_class is ObservabilityClass.TOPOLOGY_ONLY
    assert registry[LINECARD_2_ID].observability_class is ObservabilityClass.UNOBSERVED


def test_unknown_na_and_measured_zero_are_display_only() -> None:
    registry = build_observability_registry()
    full = next(item for item in registry.values() if item.observability_class is ObservabilityClass.FULL)
    power_only = next(item for item in registry.values() if item.observability_class is ObservabilityClass.POWER_ONLY)
    state_only = registry[NON_CRITICAL_PORT_ID]
    topology_only = registry[UPSTREAM_METER_ID]
    unobserved = registry[LINECARD_2_ID]

    assert full.display_power(None) == "UNKNOWN"
    assert full.display_state(None) == "UNKNOWN"
    assert power_only.display_state(None) == "N/A"
    assert state_only.display_power(None) == "N/A"
    assert topology_only.display_power(None) == "N/A"
    assert unobserved.display_power(None) == "UNKNOWN"
    assert full.display_power(0) == "0"

    yang = to_yang_instance(demo_energy_objects(), ())
    encoded = json.dumps(yang)
    assert "UNKNOWN" not in encoded
    assert "N/A" not in encoded


def test_trace_inventory_explains_missing_power_state_and_relationships() -> None:
    from green.netconf_trace import _energy_object_inventory

    data = to_yang_instance(demo_energy_objects(), ())
    inventory = "\n".join(_energy_object_inventory(data) or ())
    assert "UNKNOWN" in inventory
    assert "N/A" in inventory
    assert "eo-ai-node-1-nic-1" in inventory