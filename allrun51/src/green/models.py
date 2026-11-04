from dataclasses import dataclass
from enum import Enum


class RelationshipType(str, Enum):
    METERING = "metering"
    METERED_BY = "metered-by"
    AGGREGATING = "aggregating"
    AGGREGATED_BY = "aggregated-by"
    POWERING = "powering"
    POWERED_BY = "powered-by"
    ENABLING = "enabling"
    ENABLED_BY = "enabled-by"


RELATIONSHIP_INVERSES = {
    RelationshipType.METERING: RelationshipType.METERED_BY,
    RelationshipType.METERED_BY: RelationshipType.METERING,
    RelationshipType.AGGREGATING: RelationshipType.AGGREGATED_BY,
    RelationshipType.AGGREGATED_BY: RelationshipType.AGGREGATING,
    RelationshipType.POWERING: RelationshipType.POWERED_BY,
    RelationshipType.POWERED_BY: RelationshipType.POWERING,
    RelationshipType.ENABLING: RelationshipType.ENABLED_BY,
    RelationshipType.ENABLED_BY: RelationshipType.ENABLING,
}


class MetricType(str, Enum):
    ENERGY_CONSUMED = "energy-consumed"


class ComponentState(str, Enum):
    ACTIVE = "active"
    LOW_POWER = "low-power"
    HIBERNATING = "hibernating"
    OFF = "off"


class EventSeries(str, Enum):
    UC_2_13 = "UC 2.13"
    UC_2_10 = "UC 2.10"
    UC_2_1 = "UC 2.1"
    UC_2_2 = "UC 2.2"
    UC_2_5 = "UC 2.5"
    UC_2_6 = "UC 2.6"
    UC_2_7 = "UC 2.7"
    UC_2_8 = "UC 2.8"
    UC_2_9 = "UC 2.9"
    UC_2_11 = "UC 2.11"
    UC_2_12 = "UC 2.12"
    UC_2_14 = "UC 2.14"
    UC_2_15 = "UC 2.15"
    UC_2_16 = "UC 2.16"


class TopologyStatus(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete-topology"
    INVALID = "invalid-topology"


@dataclass(frozen=True)
class EnergyObject:
    device_id: str
    energy_object_id: str
    hardware_component_name: str | None
    hardware_component_uuid: str | None
    hardware_parent_name: str | None = None


@dataclass(frozen=True)
class EnergyRelationship:
    relationship_id: str
    relationship_type: RelationshipType
    source_energy_object_id: str
    peer_energy_object_id: str
    provenance: str


@dataclass(frozen=True)
class AccountingBoundary:
    boundary_id: str
    root_energy_object_id: str
    energy_object_ids: tuple[str, ...]


@dataclass(frozen=True)
class RawEnergyMeasurement:
    measurement_id: str
    device_id: str
    energy_object_id: str
    metric_type: MetricType
    interval_energy_wh: int
    cumulative_energy_wh: int | None
    unit: str
    time_step: str
    interval_duration_seconds: int
    timestamp_utc: str
    provenance: str
    freshness: str
    accuracy_percent: float | None = None


@dataclass(frozen=True)
class RawPowerMeasurement:
    measurement_id: str
    device_id: str
    energy_object_id: str
    instantaneous_power_w: int
    timestamp_utc: str
    provenance: str
    freshness: str


@dataclass(frozen=True)
class SimulatedEvent:
    series: EventSeries
    sequence: str
    name: str
    component_states: tuple[tuple[str, ComponentState], ...]
    measurements: tuple[RawEnergyMeasurement, ...]
    relationships: tuple[EnergyRelationship, ...]
    explanation: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    power_measurements: tuple[RawPowerMeasurement, ...] = ()
    actual_relationships: tuple[EnergyRelationship, ...] = ()
    visible_structural_relationships: tuple[EnergyRelationship, ...] = ()
    topology_ids: tuple[str, ...] = ()

    @property
    def metering_relationships(self) -> tuple[EnergyRelationship, ...]:
        return tuple(
            relationship
            for relationship in self.relationships
            if relationship.relationship_type
            in (RelationshipType.METERING, RelationshipType.METERED_BY)
        )


@dataclass(frozen=True)
class ExcludedMeasurement:
    measurement: RawEnergyMeasurement
    reason: str
    relationship_path: tuple[EnergyRelationship, ...]


@dataclass(frozen=True)
class AccountingResult:
    series: str
    event_sequence: str
    event_name: str
    boundary: AccountingBoundary
    time_step: str
    raw_measurements: tuple[RawEnergyMeasurement, ...]
    naive_total_wh: int
    accounted_total_wh: int | None
    included_measurements: tuple[RawEnergyMeasurement, ...]
    excluded_measurements: tuple[ExcludedMeasurement, ...]
    relationships_used: tuple[EnergyRelationship, ...]
    topology_status: TopologyStatus
    warnings: tuple[str, ...]
    errors: tuple[str, ...]