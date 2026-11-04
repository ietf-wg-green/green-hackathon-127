# Relationship Coverage

Relationships are stored directionally as YANG `identityref` values. Demonstration pairs include their explicit inverse; no inverse is synthesized by the views.

| Family                      | UC      | Event IDs                                                            |
| --------------------------- | ------- | -------------------------------------------------------------------- |
| metering / metered-by       | UC 2.5  | U5-0, U5-1, U5-2, U5-3, U5-4, U5-5, U5-6, U5-7                       |
| metering / metered-by       | UC 2.9  | U9-0, U9-1, U9-2, U9-3, U9-4, U9-5, U9-6, U9-7, U9-8, U9-9           |
| metering / metered-by       | UC 2.13 | U13-0, U13-1, U13-2, U13-3, U13-4, U13-5, U13-6, U13-7               |
| aggregating / aggregated-by | UC 2.6  | U6-0, U6-1, U6-2, U6-3, U6-4, U6-5, U6-6, U6-7                       |
| aggregating / aggregated-by | UC 2.11 | U11-0, U11-1, U11-2, U11-3, U11-4, U11-5, U11-6, U11-7               |
| aggregating / aggregated-by | UC 2.12 | U12-0, U12-1, U12-2, U12-3, U12-4, U12-5, U12-6, U12-7, U12-8, U12-9 |
| powering / powered-by       | UC 2.5  | U5-0, U5-1, U5-2, U5-3, U5-4, U5-5, U5-6, U5-7                       |
| powering / powered-by       | UC 2.9  | U9-0, U9-1, U9-2, U9-3, U9-4, U9-5, U9-6, U9-7, U9-8, U9-9           |
| powering / powered-by       | UC 2.14 | U14-0, U14-1, U14-2, U14-3, U14-4, U14-5, U14-6, U14-7, U14-8, U14-9 |
| enabling / enabled-by       | UC 2.9  | U9-0, U9-1, U9-2, U9-3, U9-4, U9-5, U9-6, U9-7, U9-8, U9-9           |
| enabling / enabled-by       | UC 2.10 | U10-0, U10-1, U10-2, U10-3, U10-4, U10-5, U10-6, U10-7               |
| enabling / enabled-by       | UC 2.16 | U16-0, U16-1, U16-2, U16-3, U16-4, U16-5, U16-6, U16-7, U16-8, U16-9 |

## Energy Object Details

- metering / metered-by, UC 2.5: forward `metering`, inverse `metered-by`; Energy Objects: eo-legacy-device, eo-pdu-outlet-1.
- metering / metered-by, UC 2.9: forward `metering`, inverse `metered-by`; Energy Objects: eo-ap-1, eo-poe-port-ap1.
- metering / metered-by, UC 2.13: forward `metering`, inverse `metered-by`; Energy Objects: eo-server-a, eo-server-b, eo-upstream-meter.
- aggregating / aggregated-by, UC 2.6: forward `aggregating`, inverse `aggregated-by`; Energy Objects: eo-core-domain, eo-domain-energy-aggregator, eo-transport-domain.
- aggregating / aggregated-by, UC 2.11: forward `aggregating`, inverse `aggregated-by`; Energy Objects: eo-network-energy-aggregator, eo-router-a, eo-router-b, eo-router-c.
- aggregating / aggregated-by, UC 2.12: forward `aggregating`, inverse `aggregated-by`; Energy Objects: eo-isac-energy-aggregator, eo-radar-sensor, eo-roadside-unit.
- powering / powered-by, UC 2.5: forward `powering`, inverse `powered-by`; Energy Objects: eo-legacy-device, eo-pdu-outlet-1.
- powering / powered-by, UC 2.9: forward `powering`, inverse `powered-by`; Energy Objects: eo-ap-1, eo-poe-port-ap1.
- powering / powered-by, UC 2.14: forward `powering`, inverse `powered-by`; Energy Objects: eo-backup-battery, eo-grid-source, eo-router-a, eo-router-b.
- enabling / enabled-by, UC 2.9: forward `enabling`, inverse `enabled-by`; Energy Objects: eo-ap-baseband, eo-ap-radio-24, eo-ap-radio-5.
- enabling / enabled-by, UC 2.10: forward `enabling`, inverse `enabled-by`; Energy Objects: eo-router-a-linecard-1, eo-switch-fabric.
- enabling / enabled-by, UC 2.16: forward `enabling`, inverse `enabled-by`; Energy Objects: eo-dependent-ip-function, eo-router-a, eo-transport-module.

## Accounting Semantics

Only `metering` / `metered-by` create accounting traversal edges. Aggregation, powering, and enabling remain distinct relationships and never imply metering coverage.
