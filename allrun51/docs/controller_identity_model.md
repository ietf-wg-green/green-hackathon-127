# Controller Identity Model

Controller identity is scoped by the managed device, not by a locally unique label alone.

```text
ComponentIdentity = (device_id, hardware_component_name)
EnergyObjectIdentity = (device_id, energy_object_id)
hardware_component_uuid remains a separate stable property
```

For example, `ComponentIdentity("router-A", "linecard-1")` and `ComponentIdentity("router-B", "linecard-1")` are distinct. A UUID is never substituted for a component name, Energy Object ID, or device ID.

RFC 8348 and `ietf-power-and-energy` do not define a GREEN `device_id` leaf. A controller obtains the device scope from the NETCONF managed-system/session identity and applies it out of band when reconstructing these keys. No device-side YANG change is required.
