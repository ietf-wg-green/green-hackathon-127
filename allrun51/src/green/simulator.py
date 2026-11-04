from datetime import datetime, timedelta, timezone

from green.catalog import EVENT_CATALOG, EventSpec, relationships_for_profiles
from green.canonical_network import CanonicalNetwork, load_canonical_network
from green.models import (
    ComponentState,
    EnergyObject,
    EventSeries,
    MetricType,
    RawEnergyMeasurement,
    RawPowerMeasurement,
    SimulatedEvent,
)
from green.topology import demo_energy_objects


class EventSimulator:
    def __init__(
        self,
        energy_objects: tuple[EnergyObject, ...] | None = None,
        *,
        network: CanonicalNetwork | None = None,
        use_case: EventSeries | None = None,
    ) -> None:
        self.network = network or load_canonical_network()
        self.energy_objects = energy_objects or self.network.energy_objects
        self.use_case = use_case
        self._event_specs = tuple(
            (index, spec)
            for index, spec in enumerate(EVENT_CATALOG)
            if use_case is None or spec.series is use_case
        )
        self._objects_by_id = {item.energy_object_id: item for item in self.energy_objects}
        self.reset()

    @property
    def has_next(self) -> bool:
        return self._index < len(self._event_specs)

    def peek_next(self) -> EventSpec | None:
        return self._event_specs[self._index][1] if self.has_next else None

    def reset(self) -> None:
        self._index = 0
        self._active_series = None
        self._cumulative_energy_wh = {
            item.energy_object_id: 0 for item in self.energy_objects
        }
        self._component_states: dict[str, ComponentState] = {}

    def next_event(self) -> SimulatedEvent | None:
        if not self.has_next:
            return None

        event_index, definition = self._event_specs[self._index]
        sequence = definition.sequence
        if self._active_series is not definition.series:
            self._component_states = {}
            self._active_series = definition.series
        self._component_states.update(dict(definition.component_states))
        timestamp = (
            datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(hours=event_index)
        ).isoformat()

        measurements: list[RawEnergyMeasurement] = []
        for energy_object_id, interval_energy_wh in definition.interval_energy_wh:
            energy_object = self._require_object(energy_object_id, sequence)
            cumulative_energy_wh = None
            if definition.cumulative_enabled:
                cumulative_energy_wh = (
                    self._cumulative_energy_wh[energy_object_id] + interval_energy_wh
                )
                self._cumulative_energy_wh[energy_object_id] = cumulative_energy_wh
            measurements.append(
                RawEnergyMeasurement(
                    measurement_id=f"{sequence}:{energy_object_id}",
                    device_id=energy_object.device_id,
                    energy_object_id=energy_object_id,
                    metric_type=MetricType.ENERGY_CONSUMED,
                    interval_energy_wh=interval_energy_wh,
                    cumulative_energy_wh=cumulative_energy_wh,
                    unit="Wh",
                    time_step=sequence,
                    interval_duration_seconds=3600,
                    timestamp_utc=timestamp,
                    provenance=f"{definition.series.value}-event-simulator",
                    freshness="fresh",
                )
            )

        power_measurements = tuple(
            RawPowerMeasurement(
                measurement_id=f"{sequence}:power:{energy_object_id}",
                device_id=self._require_object(energy_object_id, sequence).device_id,
                energy_object_id=energy_object_id,
                instantaneous_power_w=power_w,
                timestamp_utc=timestamp,
                provenance=f"{definition.series.value}-event-simulator",
                freshness="fresh",
            )
            for energy_object_id, power_w in definition.instantaneous_power_w
        )

        relationships = relationships_for_profiles(definition.relationship_profiles)
        actual_relationships = self.network.actual_relationships_for_profiles(
            definition.relationship_profiles
        )
        scenario = self.network.scenarios_by_uc[definition.series.value]
        self._index += 1
        return SimulatedEvent(
            series=definition.series,
            sequence=sequence,
            name=definition.name,
            component_states=tuple(sorted(self._component_states.items())),
            measurements=tuple(measurements),
            relationships=relationships,
            explanation=definition.explanation,
            metadata=definition.metadata,
            power_measurements=power_measurements,
            actual_relationships=actual_relationships,
            visible_structural_relationships=self.network.stable_structural_relationships,
            topology_ids=scenario.topology_ids,
        )

    def _require_object(self, energy_object_id: str, sequence: str) -> EnergyObject:
        try:
            return self._objects_by_id[energy_object_id]
        except KeyError as error:
            raise ValueError(
                f"event {sequence} references unknown Energy Object {energy_object_id}"
            ) from error


def generate_events(use_case: EventSeries | None = None) -> tuple[SimulatedEvent, ...]:
    simulator = EventSimulator(use_case=use_case)
    events: list[SimulatedEvent] = []
    while (event := simulator.next_event()) is not None:
        events.append(event)
    return tuple(events)
