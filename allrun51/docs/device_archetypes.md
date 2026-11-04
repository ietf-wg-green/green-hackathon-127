# Device Archetypes and Instances

Archetypes define reusable device classes; instances provide stable `device_id` values. Hardware Components and Energy Objects remain separate identities below those instances.

| Archetype          | Name                                       | Role count | Instance count |
| ------------------ | ------------------------------------------ | ---------: | -------------: |
| fixed-router       | Fixed-network router                       | 4          | 3              |
| wlan-access        | WLAN and PoE access system                 | 5          | 2              |
| power-system       | Power infrastructure and metering endpoint | 5          | 4              |
| wireless-transport | Wireless transport system                  | 4          | 2              |
| compute-node       | Compute node or cluster                    | 5          | 3              |
| service-appliance  | Media service or logical controller        | 4          | 8              |
| isac-roadside-unit | ISAC roadside unit                         | 3          | 1              |

## Archetype Details

### fixed-router - Fixed-network router

Component roles: chassis, switch-fabric, linecard, port.

Device instances:
- `router-A`
- `router-B`
- `router-C`

### wlan-access - WLAN and PoE access system

Component roles: poe-switch, poe-port, access-point, baseband, radio.

Device instances:
- `wlan-1`
- `wlan-2`

### power-system - Power infrastructure and metering endpoint

Component roles: grid-source, battery, pdu, outlet, metered-load.

Device instances:
- `legacy-device-1`
- `pdu-1`
- `power-backup`
- `power-grid`

### wireless-transport - Wireless transport system

Component roles: wireless-link, transport-module, underlay, ip-function.

Device instances:
- `microwave-site-1`
- `transport-site-1`

### compute-node - Compute node or cluster

Component roles: server, server-nic, ai-node, fabric, cluster-aggregator.

Device instances:
- `ai-training-cluster`
- `ai-training-node-1`
- `ai-training-node-2`

### service-appliance - Media service or logical controller

Component roles: video-origin, cache, domain-aggregator, controller.

Device instances:
- `access-domain-controller`
- `core-domain-controller`
- `cross-domain-controller`
- `multilayer-controller`
- `network-controller`
- `smart-city-controller`
- `transport-domain-controller`
- `video-service`

### isac-roadside-unit - ISAC roadside unit

Component roles: roadside-unit, radar-sensor, transceiver.

Device instances:
- `smart-city-site-1`

UC scenarios never redefine or rename a device instance.
