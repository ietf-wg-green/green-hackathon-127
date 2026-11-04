# GREEN Canonical Network Simulator (`allrun51`)

`allrun51/` is an isolated topology-driven GREEN simulator. All source code, YANG, data, tests, scripts, generated snapshots, runtime files, and logs stay under this directory.

The event meanings follow the upstream [draft-ietf-green-use-cases](https://github.com/emile22/draft-ietf-green-use-cases/blob/main/draft-ietf-green-use-cases.md). Event IDs and descriptions are simulator-specific and are not represented as standardized IETF events.

## Use-Case Groups

Group A is UC 2.1, 2.2, 2.5–2.16 excluding 2.3 and 2.4: **14 use cases, 122 deterministic events**. Each meets the doubled minimum event count. Group B contains only UC 2.3 and UC 2.4; they are deferred because their current text lacks enough operational detail for grounded event sequences. See [use_case_groups.md](docs/use_case_groups.md), [deferred_group_b.md](docs/deferred_group_b.md), and the generated [event_catalog.md](docs/event_catalog.md).

| UC | Events | UC | Events |
| --- | ---: | --- | ---: |
| UC 2.1 | 8 | UC 2.9 | 10 |
| UC 2.2 | 10 | UC 2.10 | 8 |
| UC 2.5 | 8 | UC 2.11 | 8 |
| UC 2.6 | 8 | UC 2.12 | 10 |
| UC 2.7 | 8 | UC 2.13 | 8 |
| UC 2.8 | 8 | UC 2.14 | 10 |
| UC 2.15 | 8 | UC 2.16 | 10 |

## Canonical Network

`DEMO-NETWORK-1` contains one stable inventory of **7 device archetypes, 23 device instances, 44 RFC 8348 Components/Energy Objects**, and six reusable sub-topologies:

| Topology | Label | Name |
| --- | --- | --- |
| T1 | CORE | Fixed Network |
| T2 | AIR | WLAN / PoE |
| T3 | POWER | Power Infrastructure |
| T4 | BACKHAUL | Wireless Transport |
| T5 | EDGE | Edge / Compute |
| T6 | CITY | ISAC / Smart City |

Sub-topologies may share device instances; use-case scenarios select primary and secondary views rather than cloning equipment.

Device archetypes and instances live separately in `data/devices/`; sub-topologies live in `data/topologies/`; UC topology overlays live in `data/scenarios/`. The detailed maps are generated in [canonical_network.md](docs/canonical_network.md), [device_archetypes.md](docs/device_archetypes.md), and [uc_topology_matrix.md](docs/uc_topology_matrix.md).

The simulator internals follow this flow:

```text
device archetypes
       ↓
device instances
       ↓
canonical topology
       ↓
UC overlays
       ↓
YANG adapter
       ↓
Sysrepo / Netopeer2
       ↓
NETCONF
```

Each event is a patch over the canonical inventory: state, measurements, relationship visibility, and simulator-only metadata may change, but device IDs, component names/UUIDs, hierarchy, Energy Object IDs, and source-component mappings remain stable. Restart resets runtime state, not inventory identity.

Controller identity is scoped as `(device_id, hardware_component_name)` for Components and `(device_id, energy_object_id)` for Energy Objects. See [controller_identity_model.md](docs/controller_identity_model.md). Relationship behavior is classified as stable structural, physical dynamic, or knowledge/observability; UC 2.13 preserves actual metering topology separately from what the controller has discovered. See [relationship_behavior_classes.md](docs/relationship_behavior_classes.md).

## Architecture

```text
Windows Python 3.11 runtime and ncclient
       | shared allrun51/runtime/operational.json
       v
WSL Sysrepo operational-data plugin
       v
WSL Netopeer2 on TCP/830
```

Windows runs the GREEN event simulator, adapter, CLI, and ncclient tests. Runtime snapshots and generated test credentials stay in `runtime/`; formatted/runtime and provider traces stay in `logs/`. Sysrepo stores the YANG modules and invokes the C operational-data provider. Netopeer2 serves NETCONF over SSH. WSL is used for native Sysrepo/Netopeer2 only; no containers are used. Windows tests prefer `localhost` and fall back to `NETCONF_HOST` from `runtime/netconf/connection.env` if WSL localhost forwarding is unavailable.

The pinned YANG revisions included in this project are:

| Module | Revision | Included file |
| --- | --- | --- |
| `ietf-power-and-energy` | `2026-07-02` | `yang/ietf-power-and-energy@2026-07-02.yang` |
| `iana-power-and-energy` | `2026-07-02` | `yang/iana-power-and-energy@2026-07-02.yang` |
| `ietf-hardware` | `2018-03-13` | `yang/ietf-hardware@2018-03-13.yang` |
| `iana-hardware` | `2018-03-13` | `yang/iana-hardware@2018-03-13.yang` |
| `ietf-inet-types` | `2013-07-15` | `yang/ietf-inet-types@2013-07-15.yang` |
| `ietf-yang-types` | `2013-07-15` | `yang/ietf-yang-types@2013-07-15.yang` |

## Setup

Create a separate Windows environment from this directory:

```powershell
cd allrun51
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

Install native dependencies once in the existing Ubuntu WSL distribution:

```bash
sudo apt update
sudo apt install -y sysrepo sysrepo-plugind netopeer2 libyang2-dev libyang2-tools build-essential pkg-config libssh-dev
```

From `allrun51/` in WSL, start/check the services:

```bash
bash scripts/wsl-netconf-start.sh
bash scripts/wsl-netconf-status.sh
```

The installer installs only missing YANG modules and creates an allrun51-specific smoke user. It stores connection details under `runtime/netconf/connection.env`; do not commit this file.

At launcher initialization, the compact WSL readiness display shows Sysrepo
and Netopeer2 process IDs plus explicit RFC 8348 hardware parent/sibling ties
using Energy Object IDs and `parent-rel-pos`.

## Runtime

```powershell
py .\allrun51\run.py
```

By default, `run.py` checks WSL health, starts the allrun51 NETCONF stack if it
is stopped or incomplete, runs pytest, then prompts between Group A events. It
stops the WSL services on every exit. To keep services running after a demo,
start them with the WSL script and run `python -m green` directly.

The launcher prefers `allrun51/.venv` when pytest, ncclient, and pyang are installed there. If that environment is incomplete, it uses the invoking interpreter and prepends `allrun51/src` to `PYTHONPATH`, so the allrun51 package is used rather than another installed GREEN package.

To run all events automatically without delay, use `py .\allrun51\run.py --auto --interval 0`.
Use `--interval SECONDS` to set another automatic-mode delay.

To run only one implemented Group A use case, pass its number with `-u` or
`--uc`, for example `py .\allrun51\run.py -u 2.13`. The same option works with
`python -m green -u 2.13`. Supported selections are UC 2.1, 2.2, and 2.5–2.16;
UC 2.3 and 2.4 remain deferred. A selected-UC run skips the full pytest suite
to avoid rerunning it after a successful test-first run; run `python -m pytest -v`
separately after changing code.

Controls:

| Input | Behavior |
| --- | --- |
| ENTER | Advance exactly one event. |
| `a` | Run all remaining Group A events across UC boundaries. |
| `d` | Toggle live operational-data tracing and append records under `logs/`. |
| `r` | Reset all scenario state and restart at UC 2.1 / U1-0. |
| `q` | Exit cleanly. |
| `summary` | Display hardware, energy objects, relationships, and UC interpretation. |
| `relationships` | Display the directional Energy Object graph. |
| `json` | Display normalized full YANG JSON. |
| `xml` | Fetch and display the actual NETCONF XML reply. |
| `diff` | Compare relationship and observed-state changes with the previous event. |

The default event display prints its UC/event ID and explanation, followed by
compact `HW`, `ENERGY`, `REL`, and `DIFF` lines. The `summary` command opens the
detailed hardware inventory, Energy Objects, relationships, and UC interpretation.

Every event has a deterministic explanation under 20 words. Runtime/controller metadata remains separate from YANG data. Missing measurements/capabilities remain unknown; interval and cumulative energy are distinct; cumulative counters reset only on `r`.

## Adding Events

To add an event to an existing Group A use case:

1. Add an `_event(...)` entry, in sequence order, to that use case's `events` tuple in [catalog.py](src/green/catalog.py). Give it a unique ID such as `U5-8`, a concise event name, and a single deterministic explanation sentence under 20 words.
2. Describe only the event's deltas: use existing Energy Object IDs for `energy`, `power`, and `states`; use `metadata` for simulator-only context; set `cumulative=True` only when the interval should advance that object's cumulative counter. Events must not create or rename inventory.
3. For relationships, reference an existing `profiles` entry in `catalog.py`. If a genuinely new relationship profile is needed, define its directional relationships and explicit inverse in `_RELATIONSHIPS`, then add or update focused UC/relationship tests. Change `data/scenarios/uc-topology-matrix.json` only if the UC's topology assignment itself changes.
4. Update the expected per-UC counts in [test_simulator.py](tests/test_simulator.py) and [test_catalog_docs.py](tests/test_catalog_docs.py). Add or extend a test under `tests/uc/` for the event's intended behavior. The catalog tests check unique IDs, sequence order, explanations, and generated documentation.
5. Regenerate the event and project docs, then run the checks:

       ```powershell
       python -m green.catalog_docs
       python scripts/generate_docs.py
       python -m pytest -v
       python -m green --auto --interval 0
       ```

The generated [event_catalog.md](docs/event_catalog.md) is documentation output; edit `catalog.py`, not that generated file. Adding a new use case is broader: it also requires a new `EventSeries`, a `UseCaseSpec`, a topology mapping, and use-case-specific tests and documentation.

## Relationship Semantics

All four YANG relationship families are represented with explicit inverse identities:

- `metering` / `metered-by`: measurement topology; only this family drives accounting de-duplication.
- `aggregating` / `aggregated-by`: aggregation of Energy Management information, not traffic concentration.
- `powering` / `powered-by`: electrical supply topology.
- `enabling` / `enabled-by`: functional dependency, not electrical power flow.

Forward and inverse links are stored as distinct directional relationships. `source-component-id` maps an Energy Object to the RFC 8348 hardware component name; it is not a relationship peer or hardware UUID. Hardware containment is represented only by RFC 8348 `parent` data. The WSL installer seeds that configuration from `yang/hardware-hierarchy.xml`; it does not infer parent links from Energy Object IDs or names. See the generated [relationship_coverage.md](docs/relationship_coverage.md).

## Capability-discovery Readiness

The [capability-discovery readiness inventory](docs/capability_discovery_readiness.md) records stable RFC 8348 Component names/UUIDs, Energy Object mappings, archetypes, topology membership, and future profile classes. This is correlation readiness only: allrun51 does not implement RFC 9196, `ietf-system-capabilities`, or `ietf-power-state-capabilities`, and UC 2.11 capability classification remains simulator/controller metadata. See [future_capability_profile_model.md](docs/future_capability_profile_model.md).

The per-object field evidence and display meanings are listed in [energy_object_observability.md](docs/energy_object_observability.md). All 44 Energy Objects have one class: `FULL`, `POWER_ONLY`, `STATE_ONLY`, `TOPOLOGY_ONLY`, or `UNOBSERVED`. `UNKNOWN` and `N/A` are display-only and are never inserted into numeric or identityref YANG leaves.

## NETCONF and Services

NETCONF is read-only in this increment. The simulator drives events and Sysrepo/Netopeer2 expose the resulting operational snapshot over `<get>`. No `<edit-config>`, custom RPC, notification, YANG Push, or RESTCONF is implemented.

From WSL:

```bash
bash scripts/wsl-netconf-status.sh
bash scripts/wsl-netconf-stop.sh
bash scripts/wsl-netconf-start.sh
```

`stop` halts `sysrepo-plugind` and `netopeer2` and clears transient service environment; installed modules, host keys, allrun51 snapshots, logs, and credentials are not deleted. `start` rebuilds the provider, installs any missing modules, refreshes the local smoke credential, and restarts the services. Run live client tests from Windows:

```powershell
.\scripts\run-netconf-smoke.ps1
```

## Tests and Validation

```powershell
python -m pytest -v
python -m green --auto --interval 0
python -m green.catalog_docs
python scripts/generate_docs.py
pyang -p yang yang\ietf-power-and-energy@2026-07-02.yang
```

The pytest suite includes 14 focused UC modules, deterministic runtime/accounting/adapter tests, relationship coverage/symmetry tests, and live `ncclient` NETCONF tests. `yanglint` can validate a generated operational instance from WSL:

```bash
yanglint -p yang \
  yang/iana-hardware@2018-03-13.yang \
  yang/ietf-hardware@2018-03-13.yang \
  yang/iana-power-and-energy@2026-07-02.yang \
  yang/ietf-power-and-energy@2026-07-02.yang \
  runtime/operational.json
```

The current capability is read-only operational simulation. Future work can refine Group B once its source text is more operationally specific and separately consider protected NETCONF control; neither is implemented here.
