from green.controller_identity import ComponentIdentity, EnergyObjectIdentity
from green.controller_reconstruction import reconstruct_from_netconf_xml
from green.models import RelationshipType


def test_controller_reconstruction_decodes_only_yang_visible_xml() -> None:
    reply = """
    <rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0"
      xmlns:h="urn:ietf:params:xml:ns:yang:ietf-hardware"
      xmlns:g="urn:ietf:params:xml:ns:yang:ietf-power-and-energy">
      <data>
        <h:hardware>
          <h:component><h:name>router-A</h:name><h:uuid>uuid-router</h:uuid></h:component>
          <h:component><h:name>linecard-1</h:name><h:uuid>uuid-linecard</h:uuid><h:parent>router-A</h:parent></h:component>
        </h:hardware>
        <g:energy-objects>
          <g:energy-object>
            <g:id>eo-router-a</g:id><g:source-component-id>router-A</g:source-component-id>
            <g:relationship><g:type>eo:enabling</g:type><g:peer><g:id>eo-linecard-1</g:id></g:peer></g:relationship>
          </g:energy-object>
          <g:energy-object><g:id>eo-linecard-1</g:id><g:source-component-id>linecard-1</g:source-component-id></g:energy-object>
        </g:energy-objects>
      </data>
    </rpc-reply>
    """

    observed = reconstruct_from_netconf_xml(reply, device_id="managed-router-1")

    assert observed.component_identities == {
        ComponentIdentity("managed-router-1", "router-A"),
        ComponentIdentity("managed-router-1", "linecard-1"),
    }
    assert observed.energy_object_identities == {
        EnergyObjectIdentity("managed-router-1", "eo-router-a"),
        EnergyObjectIdentity("managed-router-1", "eo-linecard-1"),
    }
    assert len(observed.relationships) == 1
    assert observed.relationships[0].relationship_type is RelationshipType.ENABLING