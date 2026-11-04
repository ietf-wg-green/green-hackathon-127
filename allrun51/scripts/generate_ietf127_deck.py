from html import escape
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "allrun51_ietf127_hackathon.pptx"
EMU = 914400
W, H = 13.333, 7.5
INK, PAPER, WHITE = "172722", "F4F7F2", "FFFFFF"
MUTED, GREEN, DEEP = "52645D", "B5E34A", "205B46"
CYAN, ORANGE, LINE = "48BFC1", "E88B52", "D4DED6"
HEAD, BODY = "Bahnschrift", "Aptos"


def u(value):
    return str(round(value * EMU))


def xesc(value):
    return escape(str(value), quote=True)


class Slide:
    def __init__(self, dark=False):
        self.parts = []
        self.ident = 2
        self.background = INK if dark else PAPER

    def _shape(self, x, y, w, h, geometry, fill, text_body="", outline=False):
        ident = self.ident
        self.ident += 1
        no_fill = "<a:noFill/>" if fill is None else f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
        line_xml = '<a:ln><a:noFill/></a:ln>'
        if outline:
            line_xml = f'<a:ln w="9525"><a:solidFill><a:srgbClr val="{outline}"/></a:solidFill></a:ln>'
        body = ""
        if text_body:
            body = text_body
        self.parts.append(
            f'<p:sp><p:nvSpPr><p:cNvPr id="{ident}" name="Shape {ident}"/>'
            f'<p:cNvSpPr txBox="{1 if text_body else 0}"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr><a:xfrm><a:off x="{u(x)}" y="{u(y)}"/>'
            f'<a:ext cx="{u(w)}" cy="{u(h)}"/></a:xfrm>'
            f'<a:prstGeom prst="{geometry}"><a:avLst/></a:prstGeom>{no_fill}{line_xml}</p:spPr>{body}</p:sp>'
        )

    def rect(self, x, y, w, h, fill, geometry="rect"):
        self._shape(x, y, w, h, geometry, fill)

    def text(self, value, x, y, w, h, size=12, fill=INK, bold=False,
             font=BODY, align="l"):
        ident = self.ident
        self.ident += 1
        paragraphs = []
        for line in str(value).split("\n"):
            paragraphs.append(
                f'<a:p><a:pPr algn="{align}"/><a:r><a:rPr lang="en-US" '
                f'sz="{round(size * 100)}" b="{1 if bold else 0}" dirty="0">'
                f'<a:solidFill><a:srgbClr val="{fill}"/></a:solidFill>'
                f'<a:latin typeface="{xesc(font)}"/></a:rPr>'
                f'<a:t>{xesc(line)}</a:t></a:r><a:endParaRPr lang="en-US" sz="{round(size * 100)}"/></a:p>'
            )
        body = (
            '<p:txBody><a:bodyPr wrap="square" lIns="0" rIns="0" tIns="0" bIns="0" anchor="t"/>'
            f'<a:lstStyle/>{"".join(paragraphs)}</p:txBody>'
        )
        self._shape(x, y, w, h, "rect", None, body)

    def to_xml(self):
        group = (
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
            '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        )
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            f'<p:cSld><p:bg><p:bgPr><a:solidFill><a:srgbClr val="{self.background}"/></a:solidFill>'
            '<a:effectLst/></p:bgPr></p:bg><p:spTree>'
            f'{group}{"".join(self.parts)}</p:spTree></p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'
        )


def new_slide(deck, dark=False):
    item = Slide(dark)
    deck.append(item)
    return item


def box(s, x, y, w, h, fill):
    s.rect(x, y, w, h, fill)


def txt(s, value, x, y, w, h, size=12, fill=INK, bold=False,
        font=BODY, align="l"):
    s.text(value, x, y, w, h, size, fill, bold, font, align)


def rule(s, x, y, w, thickness=0.01, fill=LINE):
    box(s, x, y, w, thickness, fill)


def heading(s, section, title, subtitle=""):
    txt(s, section.upper(), 0.62, 0.32, 7, 0.2, 9, DEEP, True)
    txt(s, title, 0.62, 0.65, 12.1, 0.55, 26, INK, True, HEAD)
    if subtitle:
        txt(s, subtitle, 0.64, 1.28, 12, 0.32, 11, MUTED)
    box(s, 0.62, 1.72, 0.58, 0.045, GREEN)


def tag(s, label, x, y, w, fill=DEEP, ink=WHITE):
    box(s, x, y, w, 0.28, fill)
    txt(s, label.upper(), x + 0.1, y + 0.055, w - 0.2, 0.16, 8, ink, True)


def footer(s, source, number, dark=False):
    rule(s, 0.62, 7.08, 12.1, 0.01, "43564B" if dark else LINE)
    tint = "B3C4B9" if dark else MUTED
    txt(s, source, 0.64, 7.15, 11.1, 0.18, 8, tint)
    txt(s, f"IETF 127 HACKATHON     {number:02d}", 10.1, 7.15, 2.6, 0.18,
        8, tint, align="r")


def cover(deck):
    s = new_slide(deck, True)
    box(s, 8.6, 0, 4.74, H, "203B30")
    box(s, 8.6, 0, 0.08, H, GREEN)
    tag(s, "IETF 127 Hackathon", 0.74, 0.62, 2.05, GREEN, INK)
    txt(s, "GREEN network\nenergy observability", 0.74, 1.55, 7.2, 1.5,
        32, WHITE, True, HEAD)
    txt(s, "A topology-driven simulator for deterministic operational scenarios",
        0.77, 3.45, 7.1, 0.65, 16, "C5D1C9")
    txt(s, "allrun51  /  project and device-map briefing", 0.77, 6.5,
        7.1, 0.25, 10, GREEN, True)
    for i, (num, label) in enumerate((("23", "device instances"),
                                       ("44", "Energy Objects"),
                                       ("122", "deterministic events"))):
        y = 1.55 + i * 1.45
        txt(s, num, 9.16, y, 2.4, 0.65, 33, GREEN, True, HEAD)
        txt(s, label, 9.21, y + 0.67, 3.1, 0.3, 12, WHITE)
        if i < 2:
            rule(s, 9.16, y + 1.18, 3.39, 0.01, "466354")
    footer(s, "Based on allrun51/README.md and docs/", 1, True)


def overview(deck):
    s = new_slide(deck)
    heading(s, "01 / Project", "One stable network. Many operational stories.",
            "Use-case events alter measurements, state, and relationship visibility, not device identity.")
    data = (("6", "reusable topologies", GREEN), ("7", "device archetypes", CYAN),
            ("23", "device instances", ORANGE), ("44", "Energy Objects", GREEN),
            ("14", "implemented use cases", CYAN), ("122", "deterministic events", ORANGE))
    for i, (value, label, accent) in enumerate(data):
        x, y = 0.66 + (i % 3) * 4.05, 2.03 + (i // 3) * 1.62
        box(s, x, y, 3.78, 1.4, WHITE)
        box(s, x, y, 0.07, 1.4, accent)
        txt(s, value, x + 0.23, y + 0.16, 3.2, 0.62, 29, INK, True, HEAD)
        txt(s, label, x + 0.24, y + 0.91, 3.2, 0.25, 11, MUTED)
    box(s, 0.66, 5.55, 12.0, 0.78, INK)
    txt(s, "SCOPE", 0.9, 5.82, 0.75, 0.2, 9, GREEN, True)
    txt(s, "14 event-ready use cases; UC 2.3 and UC 2.4 remain documented but deferred.",
        1.78, 5.78, 10.3, 0.27, 13, WHITE, True)
    footer(s, "Sources: README.md; docs/use_case_groups.md", 2)


def device_map(deck):
    s = new_slide(deck)
    heading(s, "02 / Device map", "Network devices across six topology views",
            "Membership map, not a physical-link diagram. Asterisk marks the same shared device instance.")
    groups = [
        ("T1 CORE", "Fixed network", ["router-A *", "router-B *", "router-C"], GREEN),
        ("T2 AIR", "WLAN and PoE", ["wlan-1", "wlan-2"], CYAN),
        ("T3 POWER", "Power infrastructure", ["pdu-1 *", "legacy-device-1", "power-grid",
                                                "power-backup", "router-A *", "router-B *"], ORANGE),
        ("T4 BACKHAUL", "Wireless transport", ["microwave-site-1", "transport-site-1",
                                                 "multilayer-controller", "router-A *"], GREEN),
        ("T5 EDGE", "Edge and compute", ["pdu-1 *", "cross-domain-controller",
                                           "access-domain-controller", "transport-domain-controller",
                                           "core-domain-controller", "network-controller",
                                           "video-service", "ai-training-cluster",
                                           "ai-training-node-1", "ai-training-node-2"], CYAN),
        ("T6 CITY", "ISAC and smart city", ["smart-city-controller", "smart-city-site-1"], ORANGE),
    ]
    counts = ["3 devices / 7 objects", "2 devices / 7 objects", "6 devices / 14 objects",
              "4 devices / 9 objects", "10 devices / 17 objects", "2 devices / 5 objects"]
    for i, (title, desc, devices, accent) in enumerate(groups):
        x, y = 0.66 + (i % 3) * 4.06, 2.02 + (i // 3) * 2.03
        box(s, x, y, 3.78, 1.82, WHITE)
        box(s, x, y, 3.78, 0.065, accent)
        txt(s, title, x + 0.16, y + 0.14, 1.8, 0.24, 13, INK, True, HEAD)
        txt(s, counts[i], x + 1.83, y + 0.17, 1.78, 0.18, 8, MUTED, align="r")
        txt(s, desc, x + 0.17, y + 0.45, 3.4, 0.18, 9, MUTED)
        cols = 2 if len(devices) > 4 else 1
        rows = (len(devices) + cols - 1) // cols
        for j, device in enumerate(devices):
            col, row = j // rows, j % rows
            dx, dy = x + 0.16 + col * 1.78, y + 0.74 + row * 0.22
            box(s, dx, dy, 1.68, 0.19, "EAF0EA")
            txt(s, device, dx + 0.07, dy + 0.03, 1.55, 0.13, 7.5,
                DEEP if "*" in device else INK, "*" in device)
    txt(s, "Shared instances: router-A, router-B, pdu-1. Unique inventory: 23 device instances.",
        0.7, 6.24, 12, 0.22, 10, DEEP, True)
    footer(s, "Source: docs/canonical_network.md; per-view object totals overlap", 3)


def identity(deck):
    s = new_slide(deck)
    heading(s, "03 / Identity", "Keep device, component, UUID, and Energy Object separate",
            "Controller correlation keys are scoped by the managed device.")
    entries = [("01", "Device scope", "device_id", "router-A", GREEN),
               ("02", "Component", "hardware component name", "linecard-1", CYAN),
               ("03", "Hardware UUID", "stable component UUID", "...0011", ORANGE),
               ("04", "Energy Object", "energy_object_id", "eo-router-a-linecard-1", GREEN)]
    for i, (num, title, field, example, accent) in enumerate(entries):
        x, y = 0.68 + (i % 2) * 6.1, 2.1 + (i // 2) * 1.5
        box(s, x, y, 5.72, 1.18, WHITE)
        box(s, x, y, 0.07, 1.18, accent)
        txt(s, num, x + 0.22, y + 0.2, 0.55, 0.32, 17, accent, True, HEAD)
        txt(s, title, x + 0.9, y + 0.17, 4.4, 0.28, 14, INK, True, HEAD)
        txt(s, field, x + 0.92, y + 0.58, 2.2, 0.2, 9, MUTED)
        txt(s, example, x + 3.15, y + 0.55, 2.3, 0.3, 9, DEEP, True)
    box(s, 0.7, 5.48, 11.92, 0.72, INK)
    txt(s, "Component key: (device_id, hardware_component_name)", 0.95, 5.72,
        5.45, 0.24, 12, WHITE, True, HEAD)
    txt(s, "Energy Object key: (device_id, energy_object_id)", 6.7, 5.72,
        5.55, 0.24, 12, GREEN, True, HEAD)
    txt(s, "Device scope comes from NETCONF session identity; no GREEN device_id leaf is added.",
        0.72, 6.48, 11.8, 0.22, 10, MUTED)
    footer(s, "Sources: docs/controller_identity_model.md; docs/capability_discovery_readiness.md", 4)


def architecture(deck):
    s = new_slide(deck)
    heading(s, "04 / Architecture", "From canonical inventory to a NETCONF read",
            "Windows drives events and tests; WSL runs Sysrepo and Netopeer2.")
    stages = [("Archetypes", "Reusable classes", GREEN), ("Instances", "Stable device IDs", CYAN),
              ("Topology", "Canonical network", ORANGE), ("UC overlays", "State + visibility deltas", GREEN)]
    for i, (title, detail, accent) in enumerate(stages):
        x = 0.68 + i * 3.12
        box(s, x, 2.15, 2.66, 1.05, WHITE)
        box(s, x, 2.15, 2.66, 0.07, accent)
        txt(s, title, x + 0.16, 2.43, 2.3, 0.25, 14, INK, True, HEAD)
        txt(s, detail, x + 0.16, 2.82, 2.3, 0.2, 9, MUTED)
        if i < 3:
            txt(s, ">", x + 2.74, 2.52, 0.28, 0.24, 16, DEEP, True, HEAD)
    box(s, 0.68, 3.72, 7.46, 1.2, "E4EEE5")
    tag(s, "Windows", 0.92, 3.94, 1.0)
    txt(s, "Simulator > YANG adapter > operational snapshot > ncclient", 0.95, 4.42,
        6.9, 0.25, 11, INK, True)
    box(s, 8.48, 3.72, 4.14, 1.2, "DCEFED")
    tag(s, "WSL", 8.73, 3.94, 0.65, CYAN, INK)
    txt(s, "Sysrepo provider > Netopeer2 > NETCONF / SSH", 8.75, 4.42,
        3.55, 0.25, 10, INK, True)
    box(s, 0.68, 5.42, 11.94, 0.74, INK)
    txt(s, "Read-only operational data through <get>. No <edit-config>, custom RPC, notification, YANG Push, or RESTCONF.",
        0.95, 5.66, 11.3, 0.27, 11, WHITE, True)
    footer(s, "Sources: README.md; docs/canonical_network.md", 5)


def use_cases(deck):
    s = new_slide(deck)
    heading(s, "05 / Hackathon scenarios", "Fourteen event-ready use cases",
            "Use-case groupings from the project catalog; event names are simulator-specific.")
    columns = [
        ("Observe and optimize", GREEN, [("2.1", "Incremental GREEN adoption"),
         ("2.2", "Traffic-proportional savings"), ("2.5", "Indirect energy monitoring"),
         ("2.6", "End-to-end domain metrics"), ("2.7", "Wireless transport throughput")]),
        ("Access and services", CYAN, [("2.8", "Video streaming"), ("2.9", "WLAN energy saving"),
         ("2.10", "Fixed network energy saving"), ("2.11", "Energy-efficiency management"),
         ("2.12", "ISAC smart-city traffic")]),
        ("Power and cross-layer", ORANGE, [("2.13", "Double-accounting open issue"),
         ("2.14", "Power shortage"), ("2.15", "Distributed AI workloads"),
         ("2.16", "Network cross-layer saving")])]
    for i, (title, accent, rows) in enumerate(columns):
        x = 0.66 + i * 4.06
        box(s, x, 2.0, 3.78, 3.76, WHITE)
        box(s, x, 2.0, 3.78, 0.07, accent)
        txt(s, title, x + 0.18, 2.24, 3.38, 0.28, 14, INK, True, HEAD)
        for j, (uc, name) in enumerate(rows):
            y = 2.76 + j * 0.51
            txt(s, f"UC {uc}", x + 0.2, y, 0.68, 0.2, 9, accent, True)
            txt(s, name, x + 0.95, y - 0.01, 2.6, 0.32, 9.5, INK, True)
    box(s, 0.68, 5.97, 11.94, 0.55, "F5E9DF")
    txt(s, "DEFERRED", 0.9, 6.15, 0.86, 0.18, 8, "9A4F24", True)
    txt(s, "UC 2.3 lifecycle reporting  |  UC 2.4 cloud-native real-time metering",
        1.92, 6.11, 9.9, 0.24, 10, INK, True)
    footer(s, "Sources: docs/use_case_groups.md; docs/uc_topology_matrix.md", 6)


def events(deck):
    s = new_slide(deck)
    heading(s, "06 / Event model", "Events are patches, not inventory edits",
            "A UC 2.2 sequence demonstrates traffic-aware state changes while service remains available.")
    rows = [("U2-0", "TRAFFIC PEAK", "A 500 W\nB 480 W", GREEN),
            ("U2-1", "TRAFFIC VALLEY", "A low-power\n340 W", CYAN),
            ("U2-2", "TRAFFIC RELOCATED", "Traffic shifts to B\nA falls to 250 W", ORANGE),
            ("U2-3", "COMPONENTS SLEEPING", "Unused line card\nsleeps", GREEN),
            ("U2-4", "TRAFFIC RECOVERY", "Capacity wakes\nboth paths active", CYAN)]
    for i, (event, name, detail, accent) in enumerate(rows):
        x = 0.7 + i * 2.48
        if i < 4:
            rule(s, x + 0.25, 2.62, 2.13, 0.015, LINE)
        box(s, x + 0.09, 2.47, 0.3, 0.3, accent)
        txt(s, event, x, 3.0, 2.2, 0.2, 9, accent, True)
        txt(s, name, x, 3.35, 2.2, 0.42, 11, INK, True, HEAD)
        txt(s, detail, x, 4.0, 2.2, 0.55, 10, MUTED)
    box(s, 0.7, 5.25, 11.92, 0.86, INK)
    txt(s, "STABLE", 0.96, 5.55, 0.72, 0.2, 9, GREEN, True)
    txt(s, "Device IDs | component names and UUIDs | Energy Object IDs | hierarchy", 1.84,
        5.51, 8.0, 0.25, 11, WHITE, True)
    txt(s, "Reset changes runtime state, not identity.", 9.72, 5.53, 2.5, 0.25, 9, "C5D1C9")
    footer(s, "Source: docs/UC_events_index.md; UC 2.2 example", 7)


def relationships(deck):
    s = new_slide(deck)
    heading(s, "07 / Relationship semantics", "Four families, four different meanings",
            "Links are directional identities with explicit inverses; relationships are not interchangeable.")
    rows = [("metering", "metered-by", "Measurement path", "Only family used for accounting", CYAN),
            ("aggregating", "aggregated-by", "Information aggregation", "Not traffic concentration", GREEN),
            ("powering", "powered-by", "Electrical source path", "Grid / backup can change", ORANGE),
            ("enabling", "enabled-by", "Functional dependency", "Not electrical power flow", DEEP)]
    for i, (forward, inverse, meaning, note, accent) in enumerate(rows):
        y = 2.02 + i * 0.78
        box(s, 0.68, y, 11.96, 0.62, WHITE)
        box(s, 0.68, y, 0.07, 0.62, accent)
        txt(s, forward, 0.94, y + 0.17, 1.72, 0.23, 12, INK, True, HEAD)
        txt(s, "<>", 2.75, y + 0.16, 0.4, 0.24, 12, accent, True, HEAD, "c")
        txt(s, inverse, 3.25, y + 0.17, 1.8, 0.23, 12, INK, True, HEAD)
        txt(s, meaning, 5.2, y + 0.18, 2.5, 0.22, 9.5, MUTED)
        txt(s, note, 8.05, y + 0.17, 4.3, 0.24, 9.5, DEEP, True)
    box(s, 0.68, 5.42, 5.8, 0.75, "E4EEE5")
    txt(s, "44 directional relationship entries", 0.92, 5.63, 5.25, 0.23, 14, INK, True, HEAD)
    txt(s, "24 structural  |  12 physical  |  8 observability", 0.94, 5.97, 5.2, 0.17, 8, MUTED)
    box(s, 6.72, 5.42, 5.92, 0.75, "F5E9DF")
    txt(s, "Hardware containment is separate", 6.96, 5.63, 5.3, 0.23, 13, INK, True, HEAD)
    txt(s, "Parent links do not imply GREEN relationships.", 6.98, 5.97, 5.15, 0.17, 8, MUTED)
    footer(s, "Sources: docs/relationship_coverage.md; docs/relationship_behavior_classes.md", 8)


def observability(deck):
    s = new_slide(deck)
    heading(s, "08 / Observability", "Show evidence without filling gaps with guesses",
            "All 44 Energy Objects have one evidence class. Missing telemetry is not a measured zero.")
    classes = [("FULL", "Power + state", "router-A", GREEN),
               ("POWER_ONLY", "Power", "PDU outlet", CYAN),
               ("STATE_ONLY", "State / energy", "server-A", ORANGE),
               ("TOPOLOGY_ONLY", "Relationships", "legacy target", DEEP),
               ("UNOBSERVED", "No evidence", "linecard-2", "829388")]
    for i, (name, detail, sample, accent) in enumerate(classes):
        x = 0.66 + i * 2.43
        box(s, x, 2.24, 2.18, 1.72, WHITE)
        box(s, x, 2.24, 2.18, 0.08, accent)
        txt(s, name, x + 0.15, 2.6, 1.9, 0.26, 9.5, INK, True, HEAD)
        txt(s, detail, x + 0.15, 3.07, 1.9, 0.2, 9, MUTED)
        txt(s, sample, x + 0.15, 3.48, 1.9, 0.18, 8.5, accent, True)
    box(s, 0.68, 4.4, 5.78, 1.25, INK)
    txt(s, "UNKNOWN", 0.95, 4.68, 1.1, 0.22, 12, GREEN, True, HEAD)
    txt(s, "Applicable, but not observed now.", 2.15, 4.69, 3.95, 0.22, 10, WHITE)
    txt(s, "N/A", 0.95, 5.08, 1.1, 0.22, 12, CYAN, True, HEAD)
    txt(s, "This profile does not apply the field.", 2.15, 5.09, 3.95, 0.22, 10, WHITE)
    box(s, 6.72, 4.4, 5.92, 1.25, "E4EEE5")
    txt(s, "0", 7.02, 4.68, 0.42, 0.35, 21, DEEP, True, HEAD)
    txt(s, "is a measured numeric value, not missing data.", 7.6, 4.75, 4.7, 0.25, 10, INK, True)
    txt(s, "UNKNOWN and N/A are display-only; not inserted into numeric or identityref YANG leaves.",
        0.72, 6.0, 11.8, 0.28, 9.5, MUTED)
    footer(s, "Source: docs/energy_object_observability.md", 9)


def uc13(deck):
    s = new_slide(deck)
    heading(s, "09 / Accounting edge case", "UC 2.13: physical truth is not controller knowledge",
            "Metering topology exists independently from what the event observer has discovered.")
    phases = [("01", "Topology truth", "Actual meter-to-load links remain in the canonical truth set.", GREEN),
              ("02", "Not observed", "U13-0 hides the links; the controller view is incomplete.", ORANGE),
              ("03", "Discovered", "Later overlays expose those links to the observer.", CYAN)]
    for i, (num, title, detail, accent) in enumerate(phases):
        y = 2.05 + i * 1.12
        box(s, 0.72, y, 7.2, 0.86, WHITE)
        box(s, 0.72, y, 0.08, 0.86, accent)
        txt(s, num, 0.96, y + 0.2, 0.5, 0.28, 16, accent, True, HEAD)
        txt(s, title, 1.6, y + 0.12, 1.9, 0.25, 12, INK, True, HEAD)
        txt(s, detail, 3.46, y + 0.14, 4.15, 0.48, 9.5, MUTED)
    box(s, 8.32, 2.05, 4.3, 3.08, INK)
    tag(s, "Accounting rule", 8.65, 2.38, 1.65, GREEN, INK)
    txt(s, "Traverse only\nevent-visible\nmetering edges.", 8.68, 3.02, 3.55, 1.35,
        23, WHITE, True, HEAD)
    txt(s, "No inferred coverage from powering, aggregation, or hardware containment.",
        8.68, 4.58, 3.45, 0.42, 9, "C5D1C9")
    box(s, 0.74, 5.78, 11.86, 0.54, "DCEFED")
    txt(s, "Discovery changes visibility, not the physical topology.", 0.98, 5.94,
        11.25, 0.22, 11, INK, True)
    footer(s, "Sources: docs/relationship_behavior_classes.md; docs/relationship_coverage.md; docs/UC_events_index.md", 10)


def operations(deck):
    s = new_slide(deck)
    heading(s, "10 / Demo operations", "A repeatable, read-only demonstration loop",
            "The launcher can check service health, run tests, step events, and stop WSL services on exit.")
    steps = [("1", "Prepare", "Windows Python 3.11\nProject + test extras", GREEN),
             ("2", "Start", "WSL Sysrepo\nNetopeer2 on TCP/830", CYAN),
             ("3", "Run", "Step events or run\nGroup A automatically", ORANGE),
             ("4", "Verify", "pytest + ncclient\nGET operational data", GREEN)]
    for i, (num, title, detail, accent) in enumerate(steps):
        x = 0.68 + i * 3.1
        box(s, x, 2.15, 2.72, 1.46, WHITE)
        box(s, x + 0.19, 2.38, 0.45, 0.45, accent)
        txt(s, num, x + 0.19, 2.48, 0.45, 0.17, 10, INK, True, HEAD, "c")
        txt(s, title, x + 0.78, 2.42, 1.78, 0.24, 13, INK, True, HEAD)
        txt(s, detail, x + 0.2, 3.04, 2.35, 0.4, 9, MUTED)
    box(s, 0.68, 4.05, 7.25, 1.5, INK)
    txt(s, "QUICK CHECKS", 0.95, 4.32, 2, 0.2, 9, GREEN, True)
    txt(s, "python -m pytest -v\npython -m green --auto --interval 0", 0.97, 4.75,
        6.4, 0.6, 13, WHITE, True, "Cascadia Mono")
    box(s, 8.3, 4.05, 4.31, 1.5, "F5E9DF")
    txt(s, "BOUNDARY", 8.57, 4.32, 1.2, 0.2, 9, "9A4F24", True)
    txt(s, "GET only. No configuration writes or control RPCs.", 8.57, 4.75,
        3.63, 0.56, 12, INK, True, HEAD)
    txt(s, "Runtime snapshots, logs, and generated credentials stay under allrun51/.",
        0.73, 6.0, 11.8, 0.25, 9.5, MUTED)
    footer(s, "Source: README.md", 11)


def scope(deck):
    s = new_slide(deck, True)
    txt(s, "11 / HACKATHON SCOPE", 0.7, 0.48, 6.2, 0.2, 9, GREEN, True)
    txt(s, "A useful observability base,\nwith deliberate boundaries.", 0.7, 0.94,
        9.0, 1.18, 29, WHITE, True, HEAD)
    box(s, 0.72, 2.58, 5.78, 2.48, "243B30")
    tag(s, "Implemented", 1.0, 2.88, 1.3, GREEN, INK)
    txt(s, "Stable identities and mappings\nDeterministic event overlays\nYANG operational data over NETCONF\nReadiness metadata for future profiles",
        1.02, 3.38, 5.0, 1.3, 14, WHITE, True)
    box(s, 6.8, 2.58, 5.78, 2.48, "243B30")
    tag(s, "Not implemented", 7.08, 2.88, 1.65, ORANGE, INK)
    txt(s, "RFC 9196 / system capabilities\nPower-state capability values\nCapability-gated control\nNETCONF writes or custom RPCs",
        7.1, 3.38, 5.0, 1.3, 14, WHITE, True)
    txt(s, "Open discussion", 0.75, 5.48, 2.8, 0.32, 16, GREEN, True, HEAD)
    txt(s, "Where should stable identity attach future capability profiles? Which evidence is sufficient for trustworthy accounting?",
        0.77, 5.95, 11.8, 0.48, 11, "D0DDD4")
    footer(s, "Sources: docs/capability_discovery_readiness.md; docs/future_capability_profile_model.md; docs/deferred_group_b.md", 12, True)


def package(slides):
    types = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
             '<Default Extension="xml" ContentType="application/xml"/>',
             '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
             '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
             '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
             '<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>']
    types.extend(f'<Override PartName="/ppt/slides/slide{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                 for i in range(1, len(slides) + 1))
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' + ''.join(types) + '</Types>'
    root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                 '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                 '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
                 '</Relationships>')
    slide_ids = ''.join(f'<p:sldId id="{255+i}" r:id="rId{i+1}"/>' for i in range(1, len(slides) + 1))
    presentation = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                    'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                    '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
                    f'<p:sldIdLst>{slide_ids}</p:sldIdLst><p:sldSz cx="{u(W)}" cy="{u(H)}" type="screen16x9"/>'
                    '<p:notesSz cx="6858000" cy="9144000"/><p:defaultTextStyle/></p:presentation>')
    presentation_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
                         + ''.join(f'<Relationship Id="rId{i+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{i}.xml"/>' for i in range(1, len(slides)+1))
                         + '</Relationships>')
    group_tree = ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                  '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>')
    master = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
              'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
              f'<p:cSld name="Master">{group_tree}</p:cSld>'
              '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
              '<p:sldLayoutIdLst><p:sldLayoutId id="1" r:id="rId1"/></p:sldLayoutIdLst>'
              '<p:txStyles><p:titleStyle/><p:bodyStyle/><p:otherStyle/></p:txStyles></p:sldMaster>')
    master_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                   '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>'
                   '</Relationships>')
    layout = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
              '<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
              'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">'
              f'<p:cSld name="Blank">{group_tree}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')
    layout_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
                   '</Relationships>')
    theme = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="GREEN">'
             '<a:themeElements><a:clrScheme name="GREEN"><a:dk1><a:srgbClr val="172722"/></a:dk1>'
             '<a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="205B46"/></a:dk2>'
             '<a:lt2><a:srgbClr val="F4F7F2"/></a:lt2><a:accent1><a:srgbClr val="B5E34A"/></a:accent1>'
             '<a:accent2><a:srgbClr val="48BFC1"/></a:accent2><a:accent3><a:srgbClr val="E88B52"/></a:accent3>'
             '<a:accent4><a:srgbClr val="52645D"/></a:accent4><a:accent5><a:srgbClr val="D4DED6"/></a:accent5>'
             '<a:accent6><a:srgbClr val="829388"/></a:accent6><a:hlink><a:srgbClr val="205B46"/></a:hlink>'
             '<a:folHlink><a:srgbClr val="52645D"/></a:folHlink></a:clrScheme>'
             '<a:fontScheme name="GREEN"><a:majorFont><a:latin typeface="Bahnschrift"/></a:majorFont>'
             '<a:minorFont><a:latin typeface="Aptos"/></a:minorFont></a:fontScheme>'
             '<a:fmtScheme name="GREEN"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst>'
             '<a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst>'
             '<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>'
             '<a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst>'
             '</a:fmtScheme></a:themeElements></a:theme>')
    with ZipFile(OUTPUT, 'w', ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', content_types)
        archive.writestr('_rels/.rels', root_rels)
        archive.writestr('ppt/presentation.xml', presentation)
        archive.writestr('ppt/_rels/presentation.xml.rels', presentation_rels)
        archive.writestr('ppt/slideMasters/slideMaster1.xml', master)
        archive.writestr('ppt/slideMasters/_rels/slideMaster1.xml.rels', master_rels)
        archive.writestr('ppt/slideLayouts/slideLayout1.xml', layout)
        archive.writestr('ppt/slideLayouts/_rels/slideLayout1.xml.rels', layout_rels)
        archive.writestr('ppt/theme/theme1.xml', theme)
        for i, item in enumerate(slides, 1):
            archive.writestr(f'ppt/slides/slide{i}.xml', item.to_xml())
            archive.writestr(f'ppt/slides/_rels/slide{i}.xml.rels',
                             '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                             '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                             '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
                             '</Relationships>')


def main():
    deck = []
    for build in (cover, overview, device_map, identity, architecture, use_cases,
                  events, relationships, observability, uc13, operations, scope):
        build(deck)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    package(deck)
    print(f"Created {OUTPUT} ({len(deck)} slides)")


if __name__ == "__main__":
    main()
