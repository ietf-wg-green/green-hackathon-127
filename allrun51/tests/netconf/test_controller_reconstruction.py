from green.canonical_network import load_canonical_network
from green.controller_reconstruction import reconstruct_from_netconf_xml


def test_controller_reconstructs_canonical_inventory_from_netconf_yang_only(
    netconf_manager,
    canonical_network_snapshot,
) -> None:
    reply = netconf_manager.get()
    observed = reconstruct_from_netconf_xml(
        reply.data_xml,
        device_id="DEMO-NETWORK-1",
    )
    expected = load_canonical_network()

    expected_components = {
        (item.hardware_component_name, item.hardware_component_uuid, item.hardware_parent_name)
        for item in expected.energy_objects
    }
    observed_components = {
        (item.hardware_component_name, item.hardware_component_uuid, item.hardware_parent_name)
        for item in observed.energy_objects
    }
    expected_object_ids = {item.energy_object_id for item in expected.energy_objects}
    observed_object_ids = {item.energy_object_id for item in observed.energy_objects}
    expected_structural_links = {
        (
            item.source_energy_object_id,
            item.relationship_type,
            item.peer_energy_object_id,
        )
        for item in expected.stable_structural_relationships
    }
    observed_links = {
        (
            item.source_energy_object_id,
            item.relationship_type,
            item.peer_energy_object_id,
        )
        for item in observed.relationships
    }

    assert canonical_network_snapshot == "U1-0"
    assert expected_components == observed_components
    assert expected_object_ids == observed_object_ids
    assert expected_structural_links <= observed_links
    assert len(observed.component_identities) == 44
    assert len(observed.energy_object_identities) == 44