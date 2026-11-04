# Capability-Discovery Readiness for Future caprun

This is a stable-identity readiness inventory only. allrun51 does not implement RFC 9196, `ietf-system-capabilities`, `ietf-power-state-capabilities`, capability callbacks, or capability-gated control. UC 2.11 classification remains simulator/controller metadata.

The selected Energy Objects map to RFC 8348 Components by the existing `source-component-id` leafref. Device ID, component name, UUID, and Energy Object ID remain distinct.

| Hardware component | Profile class            | UCs                                       | Topology                       |
| ------------------ | ------------------------ | ----------------------------------------- | ------------------------------ |
| `linecard-1`       | `router-linecard`        | UC 2.1, UC 2.2, UC 2.10, UC 2.11, UC 2.16 | T1 CORE, T3 POWER, T4 BACKHAUL |
| `ap-baseband`      | `ap-baseband`            | UC 2.9                                    | T2 AIR                         |
| `ap-radio-24`      | `ap-radio`               | UC 2.9                                    | T2 AIR                         |
| `ap-radio-5`       | `ap-radio`               | UC 2.9                                    | T2 AIR                         |
| `transport-module` | `transport-radio-module` | UC 2.7, UC 2.16                           | T4 BACKHAUL                    |
| `ai-node-1-nic`    | `server-nic`             | UC 2.15                                   | T5 EDGE                        |
| `radar-sensor-1`   | `isac-sensing-component` | UC 2.12                                   | T6 CITY                        |

## Component Details

### eo-router-a-linecard-1 (linecard-1)

- Device ID: `router-A`
- Hardware component name: `linecard-1`
- Hardware component UUID: `00000000-0000-4000-8000-000000000011`
- Device archetype: `fixed-router`
- Topology: T1-fixed-network, T3-power-infrastructure, T4-wireless-transport
- Energy Object ID: `eo-router-a-linecard-1`
- source-component-id: `linecard-1`
- UCs: UC 2.1, UC 2.2, UC 2.10, UC 2.11, UC 2.16
- Future capability-profile class: `router-linecard`
- Reason: Stable line-card identity supports a future router power-state profile.
- Relevant GREEN relationships:
  - eo-router-a-linecard-1 enabled-by eo-switch-fabric
  - eo-switch-fabric enabling eo-router-a-linecard-1

### eo-ap-baseband (ap-baseband)

- Device ID: `wlan-1`
- Hardware component name: `ap-baseband`
- Hardware component UUID: `00000000-0000-4000-8000-000000000044`
- Device archetype: `wlan-access`
- Topology: T2-wlan-poe
- Energy Object ID: `eo-ap-baseband`
- source-component-id: `ap-baseband`
- UCs: UC 2.9
- Future capability-profile class: `ap-baseband`
- Reason: Stable AP subsystem identity for future radio/baseband profiles.
- Relevant GREEN relationships:
  - eo-ap-baseband enabling eo-ap-radio-24
  - eo-ap-baseband enabling eo-ap-radio-5
  - eo-ap-radio-24 enabled-by eo-ap-baseband
  - eo-ap-radio-5 enabled-by eo-ap-baseband

### eo-ap-radio-24 (ap-radio-24)

- Device ID: `wlan-1`
- Hardware component name: `ap-radio-24`
- Hardware component UUID: `00000000-0000-4000-8000-000000000045`
- Device archetype: `wlan-access`
- Topology: T2-wlan-poe
- Energy Object ID: `eo-ap-radio-24`
- source-component-id: `ap-radio-24`
- UCs: UC 2.9
- Future capability-profile class: `ap-radio`
- Reason: Existing 2.4 GHz radio component exercises per-radio power modes.
- Relevant GREEN relationships:
  - eo-ap-baseband enabling eo-ap-radio-24
  - eo-ap-radio-24 enabled-by eo-ap-baseband

### eo-ap-radio-5 (ap-radio-5)

- Device ID: `wlan-1`
- Hardware component name: `ap-radio-5`
- Hardware component UUID: `00000000-0000-4000-8000-000000000046`
- Device archetype: `wlan-access`
- Topology: T2-wlan-poe
- Energy Object ID: `eo-ap-radio-5`
- source-component-id: `ap-radio-5`
- UCs: UC 2.9
- Future capability-profile class: `ap-radio`
- Reason: Existing 5 GHz radio component exercises per-radio power modes.
- Relevant GREEN relationships:
  - eo-ap-baseband enabling eo-ap-radio-5
  - eo-ap-radio-5 enabled-by eo-ap-baseband

### eo-transport-module (transport-module)

- Device ID: `transport-site-1`
- Hardware component name: `transport-module`
- Hardware component UUID: `00000000-0000-4000-8000-000000000102`
- Device archetype: `wireless-transport`
- Topology: T4-wireless-transport
- Energy Object ID: `eo-transport-module`
- source-component-id: `transport-module`
- UCs: UC 2.7, UC 2.16
- Future capability-profile class: `transport-radio-module`
- Reason: Transport module anchors future underlay and radio capability profiles.
- Relevant GREEN relationships:
  - eo-dependent-ip-function enabled-by eo-transport-module
  - eo-router-a enabled-by eo-transport-module
  - eo-transport-module enabling eo-dependent-ip-function
  - eo-transport-module enabling eo-router-a

### eo-ai-node-1-nic-1 (ai-node-1-nic)

- Device ID: `ai-training-node-1`
- Hardware component name: `ai-node-1-nic`
- Hardware component UUID: `00000000-0000-4000-8000-000000000112`
- Device archetype: `compute-node`
- Topology: T5-edge-compute
- Energy Object ID: `eo-ai-node-1-nic-1`
- source-component-id: `ai-node-1-nic`
- UCs: UC 2.15
- Future capability-profile class: `server-nic`
- Reason: Stable compute-node NIC identity is separate from workload event state.
- Relevant GREEN relationships:
  - none currently modeled

### eo-radar-sensor (radar-sensor-1)

- Device ID: `smart-city-site-1`
- Hardware component name: `radar-sensor-1`
- Hardware component UUID: `00000000-0000-4000-8000-000000000062`
- Device archetype: `isac-roadside-unit`
- Topology: T6-isac-smart-city
- Energy Object ID: `eo-radar-sensor`
- source-component-id: `radar-sensor-1`
- UCs: UC 2.12
- Future capability-profile class: `isac-sensing-component`
- Reason: Existing radar sensor is an ISAC sensing capability attachment point.
- Relevant GREEN relationships:
  - eo-isac-energy-aggregator aggregating eo-radar-sensor
  - eo-radar-sensor aggregated-by eo-isac-energy-aggregator


Future capability data belongs to a separate caprun increment. No RFC 9196 capability values are implemented or implied here.
