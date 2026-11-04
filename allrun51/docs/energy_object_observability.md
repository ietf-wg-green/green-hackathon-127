# Energy Object Observability

Classes describe evidence in the deterministic event catalog, not new YANG leaves. Display-only `UNKNOWN` means applicable but absent from the current observation; `N/A` means the observability profile intentionally does not apply the field. Numeric zero remains the measured value `0`.

| Energy Object                     | Class           | Power | State | Energy | Relationships |
| --------------------------------- | --------------- | ----- | ----- | ------ | ------------- |
| `eo-upstream-meter`               | `TOPOLOGY_ONLY` | no    | no    | yes    | yes           |
| `eo-server-a`                     | `TOPOLOGY_ONLY` | no    | no    | yes    | yes           |
| `eo-server-b`                     | `TOPOLOGY_ONLY` | no    | no    | yes    | yes           |
| `eo-router-a`                     | `FULL`          | yes   | yes   | no     | yes           |
| `eo-router-a-linecard-1`          | `FULL`          | yes   | yes   | no     | yes           |
| `eo-router-a-linecard-2`          | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-router-b`                     | `FULL`          | yes   | yes   | no     | yes           |
| `eo-router-b-switchable-port`     | `STATE_ONLY`    | no    | yes   | no     | no            |
| `eo-pdu-1`                        | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-pdu-outlet-1`                 | `POWER_ONLY`    | yes   | no    | no     | yes           |
| `eo-ai-node-1-nic-1`              | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-legacy-device`                | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-poe-switch`                   | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-poe-port-ap1`                 | `FULL`          | yes   | yes   | no     | yes           |
| `eo-ap-1`                         | `FULL`          | yes   | yes   | no     | yes           |
| `eo-ap-2`                         | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-ap-baseband`                  | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-ap-radio-24`                  | `STATE_ONLY`    | no    | yes   | no     | yes           |
| `eo-ap-radio-5`                   | `STATE_ONLY`    | no    | yes   | no     | yes           |
| `eo-domain-energy-aggregator`     | `POWER_ONLY`    | yes   | no    | no     | yes           |
| `eo-access-domain`                | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-transport-domain`             | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-core-domain`                  | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-network-energy-aggregator`    | `POWER_ONLY`    | yes   | no    | no     | yes           |
| `eo-router-c`                     | `POWER_ONLY`    | yes   | no    | no     | yes           |
| `eo-isac-energy-aggregator`       | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-roadside-unit`                | `POWER_ONLY`    | yes   | no    | no     | yes           |
| `eo-radar-sensor`                 | `FULL`          | yes   | yes   | no     | yes           |
| `eo-isac-transceiver`             | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-city-traffic-controller`      | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-wireless-link-1`              | `FULL`          | yes   | yes   | no     | no            |
| `eo-video-origin-1`               | `POWER_ONLY`    | yes   | no    | no     | no            |
| `eo-video-cache-1`                | `POWER_ONLY`    | yes   | no    | no     | no            |
| `eo-ai-cluster-energy-aggregator` | `POWER_ONLY`    | yes   | no    | no     | no            |
| `eo-ai-node-1`                    | `FULL`          | yes   | yes   | no     | no            |
| `eo-ai-node-2`                    | `FULL`          | yes   | yes   | no     | no            |
| `eo-ai-fabric`                    | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-ip-overlay`                   | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-transport-underlay`           | `UNOBSERVED`    | no    | no    | no     | no            |
| `eo-transport-module`             | `FULL`          | yes   | yes   | no     | yes           |
| `eo-dependent-ip-function`        | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-switch-fabric`                | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-grid-source`                  | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |
| `eo-backup-battery`               | `TOPOLOGY_ONLY` | no    | no    | no     | yes           |

## Object Details

### eo-upstream-meter

- Device ID: `pdu-1`
- Hardware component: `upstream-meter`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: observed
- Relationship evidence: defined

### eo-server-a

- Device ID: `pdu-1`
- Hardware component: `server-A`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: observed
- Relationship evidence: defined

### eo-server-b

- Device ID: `pdu-1`
- Hardware component: `server-B`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: observed
- Relationship evidence: defined

### eo-router-a

- Device ID: `router-A`
- Hardware component: `router-A`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-router-a-linecard-1

- Device ID: `router-A`
- Hardware component: `linecard-1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-router-a-linecard-2

- Device ID: `router-A`
- Hardware component: `linecard-2`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-router-b

- Device ID: `router-B`
- Hardware component: `router-B`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-router-b-switchable-port

- Device ID: `router-B`
- Hardware component: `switchable-port`
- Class: `STATE_ONLY`
- Power evidence: not observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-pdu-1

- Device ID: `pdu-1`
- Hardware component: `pdu-1`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-pdu-outlet-1

- Device ID: `pdu-1`
- Hardware component: `pdu-outlet-1`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-ai-node-1-nic-1

- Device ID: `ai-training-node-1`
- Hardware component: `ai-node-1-nic`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-legacy-device

- Device ID: `legacy-device-1`
- Hardware component: `legacy-device`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-poe-switch

- Device ID: `wlan-1`
- Hardware component: `poe-switch`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-poe-port-ap1

- Device ID: `wlan-1`
- Hardware component: `poe-port-ap1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-ap-1

- Device ID: `wlan-1`
- Hardware component: `ap-1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-ap-2

- Device ID: `wlan-2`
- Hardware component: `ap-2`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ap-baseband

- Device ID: `wlan-1`
- Hardware component: `ap-baseband`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-ap-radio-24

- Device ID: `wlan-1`
- Hardware component: `ap-radio-24`
- Class: `STATE_ONLY`
- Power evidence: not observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-ap-radio-5

- Device ID: `wlan-1`
- Hardware component: `ap-radio-5`
- Class: `STATE_ONLY`
- Power evidence: not observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-domain-energy-aggregator

- Device ID: `cross-domain-controller`
- Hardware component: `domain-energy-aggregator`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-access-domain

- Device ID: `access-domain-controller`
- Hardware component: `access-domain`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-transport-domain

- Device ID: `transport-domain-controller`
- Hardware component: `transport-domain`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-core-domain

- Device ID: `core-domain-controller`
- Hardware component: `core-domain`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-network-energy-aggregator

- Device ID: `network-controller`
- Hardware component: `network-energy-aggregator`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-router-c

- Device ID: `router-C`
- Hardware component: `router-C`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-isac-energy-aggregator

- Device ID: `smart-city-controller`
- Hardware component: `isac-energy-aggregator`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-roadside-unit

- Device ID: `smart-city-site-1`
- Hardware component: `roadside-unit-1`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-radar-sensor

- Device ID: `smart-city-site-1`
- Hardware component: `radar-sensor-1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-isac-transceiver

- Device ID: `smart-city-site-1`
- Hardware component: `isac-transceiver-1`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-city-traffic-controller

- Device ID: `smart-city-controller`
- Hardware component: `city-traffic-controller`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-wireless-link-1

- Device ID: `microwave-site-1`
- Hardware component: `wireless-link-1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-video-origin-1

- Device ID: `video-service`
- Hardware component: `video-origin-1`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-video-cache-1

- Device ID: `video-service`
- Hardware component: `video-cache-1`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ai-cluster-energy-aggregator

- Device ID: `ai-training-cluster`
- Hardware component: `ai-cluster-energy-aggregator`
- Class: `POWER_ONLY`
- Power evidence: observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ai-node-1

- Device ID: `ai-training-node-1`
- Hardware component: `ai-node-1`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ai-node-2

- Device ID: `ai-training-node-2`
- Hardware component: `ai-node-2`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ai-fabric

- Device ID: `ai-training-cluster`
- Hardware component: `ai-fabric`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-ip-overlay

- Device ID: `multilayer-controller`
- Hardware component: `ip-overlay`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-transport-underlay

- Device ID: `multilayer-controller`
- Hardware component: `transport-underlay`
- Class: `UNOBSERVED`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: not defined

### eo-transport-module

- Device ID: `transport-site-1`
- Hardware component: `transport-module`
- Class: `FULL`
- Power evidence: observed
- State evidence: observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-dependent-ip-function

- Device ID: `multilayer-controller`
- Hardware component: `dependent-ip-function`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-switch-fabric

- Device ID: `router-A`
- Hardware component: `switch-fabric`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-grid-source

- Device ID: `power-grid`
- Hardware component: `grid-source`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined

### eo-backup-battery

- Device ID: `power-backup`
- Hardware component: `backup-battery`
- Class: `TOPOLOGY_ONLY`
- Power evidence: not observed
- State evidence: not observed
- Energy evidence: not observed
- Relationship evidence: defined


Class semantics: `FULL` has event evidence of both instantaneous Power and power State; `POWER_ONLY` has Power evidence; `STATE_ONLY` has State evidence; `TOPOLOGY_ONLY` has interval/cumulative Energy or relationship evidence but no Power/State evidence; `UNOBSERVED` has no event measurement, state, or relationship evidence beyond inventory identity.

Counts: FULL=10, POWER_ONLY=8, STATE_ONLY=3, TOPOLOGY_ONLY=12, UNOBSERVED=11
