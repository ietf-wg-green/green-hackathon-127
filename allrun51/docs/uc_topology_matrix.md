# UC-to-Topology Matrix

## Use Case Names

| UC      | Name                                                                   |
| ------- | ---------------------------------------------------------------------- |
| UC 2.1  | Incremental Application of the GREEN Framework                         |
| UC 2.2  | Selective reduction of energy consumption proportional to traffic      |
| UC 2.5  | Indirect Energy Monitoring and control                                 |
| UC 2.6  | Consideration of other domains for obtention of end-to-end metrics     |
| UC 2.7  | Dynamic adjustment of network element throughput in wireless transport |
| UC 2.8  | Video streaming use case                                               |
| UC 2.9  | WLAN Network Energy Saving                                             |
| UC 2.10 | Fixed Network Energy Saving                                            |
| UC 2.11 | Energy Efficiency Network Management                                   |
| UC 2.12 | ISAC-enabled Energy-Aware Smart City Traffic Management                |
| UC 2.13 | Double Accounting Open issue                                           |
| UC 2.14 | Energy Efficiency Under Power Shortage                                 |
| UC 2.15 | Energy-Efficient Management of Distributed AI Training Workloads       |
| UC 2.16 | Network-level Cross Layer Energy Saving                                |

## Topology Assignment Summary

| UC      | Primary          | Secondary       | Events |
| ------- | ---------------- | --------------- | -----: |
| UC 2.1  | T1 CORE          | -               | 8      |
| UC 2.2  | T1 CORE          | T2 AIR          | 10     |
| UC 2.5  | T2 AIR           | T3 POWER        | 8      |
| UC 2.6  | T1 CORE, T5 EDGE | T6 CITY         | 8      |
| UC 2.7  | T4 BACKHAUL      | -               | 8      |
| UC 2.8  | T5 EDGE          | T1 CORE         | 8      |
| UC 2.9  | T2 AIR           | T3 POWER        | 10     |
| UC 2.10 | T1 CORE          | -               | 8      |
| UC 2.11 | All (T1-T6)      | -               | 8      |
| UC 2.12 | T6 CITY          | T4 BACKHAUL     | 10     |
| UC 2.13 | T5 EDGE          | T3 POWER        | 8      |
| UC 2.14 | T3 POWER         | T1 CORE, T2 AIR | 10     |
| UC 2.15 | T5 EDGE          | T1 CORE         | 8      |
| UC 2.16 | T1 CORE          | T4 BACKHAUL     | 10     |

UC 2.11 uses the full canonical network. Group B UCs 2.3 and 2.4 remain deferred.
