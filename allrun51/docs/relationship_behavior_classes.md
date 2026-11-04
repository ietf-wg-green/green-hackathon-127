# Relationship Behavior Classes

| Behavior class          | Links | Relationship types                               |
| ----------------------- | ----: | ------------------------------------------------ |
| stable-structural       | 24    | aggregated-by, aggregating, enabled-by, enabling |
| physical-dynamic        | 12    | powered-by, powering                             |
| knowledge-observability | 8     | metered-by, metering                             |

## Class Semantics

- `stable-structural`: Persistent functional structure, including aggregation and enabling dependencies.
- `physical-dynamic`: The active electrical source path; UC 2.14 changes grid/battery links as state changes.
- `knowledge-observability`: Physical metering links whose controller visibility can be incomplete or discovered later.

Hardware `parent` containment does not imply metering, aggregation, powering, or enabling.

## UC 2.13 Discovery

The canonical physical metering topology exists independently of controller visibility. U13-0 keeps the actual links in the topology truth set while exposing no metering links to the event observer; later discovery overlays expose the links. Accounting uses only event-visible relationships, so incomplete knowledge remains incomplete rather than fabricating a physical topology change.
