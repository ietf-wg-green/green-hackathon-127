# Future Capability Profile Model

Future capability data belongs to stable device archetypes or hardware component instances, joined by RFC 8348 identity. It does not belong to UC names or event IDs.

| Capability profile class | Attachment point in allrun51                          |
| ------------------------ | ----------------------------------------------------- |
| router-linecard          | fixed-router / `linecard-1` Component                 |
| ap-radio                 | WLAN access / `ap-radio-24` or `ap-radio-5` Component |
| ap-baseband              | WLAN access / `ap-baseband` Component                 |
| transport-radio-module   | wireless transport / `transport-module` Component     |
| server-nic               | compute node / `ai-node-1-nic` Component              |
| isac-sensing-component   | ISAC roadside unit / `radar-sensor-1` Component       |

Bad: UC 2.10 capability profile or U16-6 capability profile. Good: router-linecard or transport-radio-module profile.

allrun51 implements readiness metadata only. It does not implement RFC 9196, `ietf-system-capabilities`, `ietf-power-state-capabilities`, or capability values, and does not derive capability from operational UC state.
