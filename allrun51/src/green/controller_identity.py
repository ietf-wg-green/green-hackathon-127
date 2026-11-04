from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class ComponentIdentity:
    device_id: str
    hardware_component_name: str


@dataclass(frozen=True, order=True)
class EnergyObjectIdentity:
    device_id: str
    energy_object_id: str