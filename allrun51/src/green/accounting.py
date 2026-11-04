from collections.abc import Sequence

from green.models import (
    AccountingBoundary,
    AccountingResult,
    EnergyRelationship,
    ExcludedMeasurement,
    RawEnergyMeasurement,
    TopologyStatus,
)
from green.topology import RelationshipGraph


class MeasurementValidationError(ValueError):
    """Raised when measurements cannot be compared for one interval."""


class AccountingEngine:
    def compute(
        self,
        boundary: AccountingBoundary,
        measurements: Sequence[RawEnergyMeasurement],
        topology: RelationshipGraph,
        *,
        series: str,
        event_sequence: str,
        event_name: str,
    ) -> AccountingResult:
        raw_measurements = tuple(measurements)
        if not raw_measurements:
            raise MeasurementValidationError("no measurements provided")
        if len(set(boundary.energy_object_ids)) != len(boundary.energy_object_ids):
            raise MeasurementValidationError("accounting boundary contains duplicate Energy Object IDs")
        if boundary.root_energy_object_id not in boundary.energy_object_ids:
            raise MeasurementValidationError("accounting boundary root is outside its declared scope")

        by_object_id: dict[str, RawEnergyMeasurement] = {}
        for measurement in raw_measurements:
            if measurement.energy_object_id in by_object_id:
                raise MeasurementValidationError(
                    f"duplicate measurement for {measurement.energy_object_id}"
                )
            by_object_id[measurement.energy_object_id] = measurement

        expected_ids = set(boundary.energy_object_ids)
        actual_ids = set(by_object_id)
        if actual_ids != expected_ids:
            missing = sorted(expected_ids - actual_ids)
            extra = sorted(actual_ids - expected_ids)
            raise MeasurementValidationError(
                f"measurement scope mismatch; missing={missing}, outside_boundary={extra}"
            )

        first = raw_measurements[0]
        for measurement in raw_measurements:
            if measurement.metric_type != first.metric_type:
                raise MeasurementValidationError("cannot combine different metric types")
            if measurement.unit != first.unit:
                raise MeasurementValidationError("cannot combine measurements with different units")
            if measurement.time_step != first.time_step:
                raise MeasurementValidationError("cannot combine different measurement time steps")
            if measurement.interval_duration_seconds != first.interval_duration_seconds:
                raise MeasurementValidationError("cannot combine different interval durations")
            if measurement.interval_energy_wh < 0:
                raise MeasurementValidationError("consumed interval energy cannot be negative")

        naive_total = sum(
            by_object_id[object_id].interval_energy_wh
            for object_id in boundary.energy_object_ids
        )

        def build_result(
            topology_status: TopologyStatus,
            *,
            accounted_total: int | None = None,
            included: tuple[RawEnergyMeasurement, ...] = (),
            excluded: tuple[ExcludedMeasurement, ...] = (),
            relationships_used: tuple[EnergyRelationship, ...] = (),
            warnings: tuple[str, ...] = (),
            errors: tuple[str, ...] = (),
        ) -> AccountingResult:
            return AccountingResult(
                series=series,
                event_sequence=event_sequence,
                event_name=event_name,
                boundary=boundary,
                time_step=event_sequence,
                raw_measurements=raw_measurements,
                naive_total_wh=naive_total,
                accounted_total_wh=accounted_total,
                included_measurements=included,
                excluded_measurements=excluded,
                relationships_used=relationships_used,
                topology_status=topology_status,
                warnings=warnings,
                errors=errors,
            )

        if topology.validation_errors:
            return build_result(TopologyStatus.INVALID, errors=topology.validation_errors)

        root_id = boundary.root_energy_object_id
        missing_objects = expected_ids - topology.energy_object_ids
        if root_id not in topology.energy_object_ids or missing_objects:
            missing = sorted(
                missing_objects | ({root_id} if root_id not in topology.energy_object_ids else set())
            )
            return build_result(
                TopologyStatus.INCOMPLETE,
                warnings=(f"Energy Objects missing from topology: {', '.join(missing)}",),
            )

        paths = topology.metering_paths_from(root_id)
        unreachable = expected_ids - {root_id} - set(paths)
        if unreachable:
            return build_result(
                TopologyStatus.INCOMPLETE,
                warnings=(
                    "no explicit metering path from accounting boundary root to: "
                    + ", ".join(sorted(unreachable)),
                ),
            )

        included = (by_object_id[root_id],)
        excluded = tuple(
            ExcludedMeasurement(
                measurement=by_object_id[object_id],
                reason=(
                    f"explicit metering topology from {root_id} covers this downstream "
                    "observation; do not add it again"
                ),
                relationship_path=paths[object_id],
            )
            for object_id in boundary.energy_object_ids
            if object_id != root_id
        )
        relationships_used_list = []
        seen_relationship_ids: set[str] = set()
        for exclusion in excluded:
            for relationship in exclusion.relationship_path:
                if relationship.relationship_id not in seen_relationship_ids:
                    relationships_used_list.append(relationship)
                    seen_relationship_ids.add(relationship.relationship_id)

        return build_result(
            TopologyStatus.COMPLETE,
            accounted_total=by_object_id[root_id].interval_energy_wh,
            included=included,
            excluded=excluded,
            relationships_used=tuple(relationships_used_list),
        )