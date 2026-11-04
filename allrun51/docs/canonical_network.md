# Canonical Demo Network

`DEMO-NETWORK-1` is one stable logical network composed of 6 reusable sub-topologies.

| Topology    | Name                 | Devices | Energy Objects |
| ----------- | -------------------- | ------: | -------------: |
| T1 CORE     | Fixed network        | 3       | 7              |
| T2 AIR      | WLAN and PoE         | 2       | 7              |
| T3 POWER    | Power infrastructure | 6       | 14             |
| T4 BACKHAUL | Wireless transport   | 4       | 9              |
| T5 EDGE     | Edge and compute     | 10      | 17             |
| T6 CITY     | ISAC and smart city  | 2       | 5              |

Sub-topologies may share a stable device instance; the UC mapping selects a primary view and optional supporting views without cloning the device inventory.
RFC 8348 containment and GREEN Energy Object relationships are modeled separately. The topology registry supplies stable identities; event definitions supply only dynamic overlays.

## Topology Details

### T1 CORE - Fixed network

Topology ID: `T1-fixed-network`.

Device instances:
- `router-A` - Router A
- `router-B` - Router B
- `router-C` - Router C
Relationship profiles: uc10, network-management.

### T2 AIR - WLAN and PoE

Topology ID: `T2-wlan-poe`.

Device instances:
- `wlan-1` - WLAN access system 1
- `wlan-2` - WLAN access point 2
Relationship profiles: wlan.

### T3 POWER - Power infrastructure

Topology ID: `T3-power-infrastructure`.

Device instances:
- `pdu-1` - PDU and metering system
- `legacy-device-1` - Legacy metered device
- `power-grid` - Grid power source
- `power-backup` - Backup power source
- `router-A` - Router A
- `router-B` - Router B
Relationship profiles: pdu-indirect, grid-source, battery-source, uc13-full, uc13-partial.

### T4 BACKHAUL - Wireless transport

Topology ID: `T4-wireless-transport`.

Device instances:
- `microwave-site-1` - Microwave site 1
- `transport-site-1` - Transport site 1
- `multilayer-controller` - Multilayer controller
- `router-A` - Router A
Relationship profiles: cross-layer.

### T5 EDGE - Edge and compute

Topology ID: `T5-edge-compute`.

Device instances:
- `pdu-1` - PDU and metering system
- `cross-domain-controller` - Cross-domain controller
- `access-domain-controller` - Access domain controller
- `transport-domain-controller` - Transport domain controller
- `core-domain-controller` - Core domain controller
- `network-controller` - Network management controller
- `video-service` - Video service
- `ai-training-cluster` - AI training cluster
- `ai-training-node-1` - AI training node 1
- `ai-training-node-2` - AI training node 2
Relationship profiles: cross-domain, network-management, uc10, uc13-full, uc13-partial.

### T6 CITY - ISAC and smart city

Topology ID: `T6-isac-smart-city`.

Device instances:
- `smart-city-controller` - Smart city controller
- `smart-city-site-1` - Smart city roadside site 1
Relationship profiles: isac.
