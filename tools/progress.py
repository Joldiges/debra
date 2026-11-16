#!/usr/bin/env python3
"""Build the public Mermaid progress view from tracked planning/execution docs.

Standard library only. No Git state, private registry, network or device access.
Titles and overview layout below are presentation, never task state or ownership.
"""

import argparse
from collections import Counter
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = "docs/progress.md"
PACKET = r"[A-Z]+\d{2}"
STATES = {
    "done": "finished", "ready": "untouched", "blocked": "blocked",
    "review": "review", "prototype": "partial",
}
# Fill, outline, visible label. Text accompanies colour for monochrome readers.
STYLES = {
    "finished": ("#dcfce7", "#166534", "FINISHED"),
    "running": ("#dbeafe", "#1e40af", "IN PROGRESS"),
    "review": ("#f3e8ff", "#7e22ce", "IN REVIEW"),
    "partial": ("#fef3c7", "#92400e", "PARTIAL"),
    "blocked": ("#fee2e2", "#991b1b", "BLOCKED"),
    "untouched": ("#f1f5f9", "#475569", "UNTOUCHED"),
}
TITLES = {
    "F00": "Planning foundation", "F01": "Clean base and ownership",
    "F02": "Architecture decisions", "F03": "Shared contracts and test layout",
    "F04": "License and provenance", "F05": "Worker permission pilot",
    "F06": "Project-scoped agent permissions",
    "R01": "Parts inventory and cost", "R02": "Complete alternatives",
    "R03": "Music transports and servers", "R04": "Upstream reuse",
    "R05": "Comparisons and choose-your-path", "R06": "Beginner and builder guides",
    "R07": "Alternative boards",
    "L01": "Lab inventory, scope and recovery", "L02": "Device binding and leases",
    "L03": "Repeatable lab reset",
    "N01": "Onboarding research", "N02": "Identity and setup prototype",
    "N03": "Unique accounts and SSH keys", "N04": "Physical onboarding trials",
    "N05": "Development Imager-to-SSH path", "N06": "Reliable headless provisioning",
    "C01": "Validated shared configuration", "C02": "Component operations",
    "C03": "CLI and dry runs", "C04": "SSH maintenance TUI",
    "C05": "Sanitized diagnostics",
    "WEB01": "Native volume and mute", "WEB02": "Address and browser enrollment",
    "WEB03": "Hardware selection and detection", "WEB04": "Component state",
    "WEB05": "Audio and voice settings", "WEB06": "LEDs and physical controls",
    "WEB07": "Health and resource readings", "WEB08": "Browser updates and restore",
    "WEB09": "Accessibility and browser security", "WEB10": "Shared browser/CLI authority",
    "A01": "Exact-board audio baseline", "A02": "Tested HAT profiles",
    "A03": "Duck or pause, then resume", "A04": "HAT LEDs, buttons and mute",
    "V01": "Voice runtime audit", "V02": "Pinned voice adapter",
    "V03": "Wake and satellite options", "V04": "Timers, alarms and announcements",
    "M01": "Pinned Sendspin adapter", "M02": "Multiroom measurements",
    "M03": "Optional Snapcast adapter", "M04": "Multi-stack coexistence",
    "Z01": "ARMv6 dependency reconnaissance", "Z02": "Missing-artifact build recipes",
    "Z03": "Execute on original Zero W", "Z04": "Zero W resource and audio profiling",
    "Z05": "Resolve bottlenecks and retest",
    "B01": "Recovery backend research", "B02": "Capture/verify/restore interface",
    "B03": "Demonstrate on-target file restore", "B04": "Pre-change checkpoints",
    "B05": "Deferred rescue and media-loss recovery",
    "U01": "Version pins and update planning", "U02": "Manual update and rollback",
    "U03": "Per-component opt-in auto-update",
    "I01": "Prepared-image design", "I02": "Reproducible image recipe",
    "I03": "Two-board flash and boot trial", "I04": "Candidate packaging and notices",
    "T01": "Acceptance matrix and test tiers", "T02": "Repeatable integrated slice",
    "T03": "Failure and soak tests", "T04": "Offline CI",
    "T05": "Fresh-user rehearsal",
    "D01": "Dimensions and CAD provenance", "D02": "Editable enclosure designs",
    "D03": "Physical fit, thermal and audio tests",
}

# Simplified capability flow. Exact packet dependencies come ONLY from roadmap.
STAGES = {
    "plan": ("Planning foundation", ("F00", "F01")),
    "research": ("Research and acceptance design",
                 ("R01", "R02", "R03", "R04", "R07", "N01", "B01", "T01")),
    "contracts": ("Architecture and shared contracts", ("F02", "F03", "F04")),
    "lab": ("Repeatable lab and card preparation", ("L01", "L02", "L03", "N05", "N06")),
    "setup": ("First boot, identity and Wi-Fi", ("N02", "N03", "N04")),
    "recovery": ("On-target file recovery", ("B02", "B03", "B04")),
    "core": ("Shared configuration and operations", ("C01", "C02", "C03", "WEB10")),
    "audio": ("Audio and HAT profiles", ("A01", "A02")),
    "voice": ("Home Assistant voice", ("V01", "V02", "V03", "V04")),
    "music": ("Sendspin, multiroom and Snapcast", ("M01", "M02", "M03", "M04")),
    "coexist": ("Interruption and HAT controls", ("A03", "A04")),
    "browser": ("Everyday browser controls", tuple(f"WEB{i:02}" for i in range(1, 10))),
    "maintenance": ("Maintenance, diagnostics and updates", ("C04", "C05", "U01", "U02", "U03")),
    "image": ("Prepared image and boot validation", ("I01", "I02", "I03")),
    "testing": ("Integration, failure tests and user trial", ("T02", "T03", "T04", "T05")),
    "guides": ("Comparisons and usable guides", ("R05", "R06")),
    "candidate": ("Packaged product candidate", ("I04",)),
    "zero": ("Full original Zero W support", tuple(f"Z{i:02}" for i in range(1, 6))),
    "case": ("Enclosure variants", ("D01", "D02", "D03")),
    "agents": ("Development permission pilots", ("F05", "F06")),
    "rescue": ("Deferred rescue and media-loss recovery", ("B05",)),
}
OVERVIEW_EDGES = (
    ("plan", "research"), ("research", "contracts"), ("contracts", "core"),
    ("contracts", "lab"), ("contracts", "setup"), ("contracts", "recovery"),
    ("lab", "audio"), ("core", "audio"), ("audio", "voice"), ("audio", "music"),
    ("voice", "coexist"), ("music", "coexist"), ("core", "browser"),
    ("core", "maintenance"), ("recovery", "maintenance"),
    ("setup", "image"), ("core", "image"),
    ("voice", "testing"), ("music", "testing"), ("coexist", "testing"),
    ("browser", "testing"), ("maintenance", "testing"), ("image", "testing"),
    ("research", "guides"), ("testing", "guides"),
    ("testing", "candidate"), ("guides", "candidate"),
)
PARALLEL = ("zero", "case", "agents", "rescue")


@dataclass(frozen=True)
class Task:
    id: str
    state: str
    dependencies: tuple
    conditional: frozenset
    dependency_text: str
    section: str
    progress: str


def require(condition, message):
    if not condition:
        raise ValueError(message)


PACKET_HEADER = "ID / state"


def is_separator(cells):
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def split_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def table_rows(text):
    """Yield heading, cells and table header outside fenced examples.

    The header is carried because not every table in the roadmap is a packet
    table: the component-candidate table has a row `SHT40 / BME280
    environmental sensors`, whose first cell has the shape of a packet id and
    state. Only a table headed `ID / state` defines packet state, so the header
    decides, not the shape of the row.

    A row is a header when the next line is a separator. A single-row table
    with no separator is yielded as data with `header` set to None, which is
    what the queue fixtures in the tests are.
    """
    lines = text.splitlines()
    section = ""
    fence = None
    header = None
    for index, line in enumerate(lines):
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token[0]
            elif fence == token[0]:
                fence = None
            continue
        if fence:
            continue
        if line.startswith("## "):
            section = line[3:].strip()
        if not line.startswith("|"):
            header = None
            continue
        cells = split_row(line)
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if following.startswith("|") and is_separator(split_row(following)):
            header = cells[0]
            continue
        if is_separator(cells):
            continue
        yield section, cells, header


def parse_roadmap(text):
    tasks = {}
    annotations = {}
    for section, cells, header in table_rows(text):
        if section == "Visual progress annotations" and re.fullmatch(PACKET, cells[0]):
            key = cells[0]
            require(len(cells) >= 3 and cells[1] == "partial" and cells[2],
                    f"Invalid progress annotation: {key}")
            require(key not in annotations, f"Duplicate progress annotation: {key}")
            annotations[key] = cells[1]
            continue
        if header != PACKET_HEADER:
            continue
        match = re.fullmatch(rf"({PACKET}) / (.+)", cells[0])
        if not match:
            continue
        key, state = match.groups()
        require(len(cells) >= 3, f"Incomplete roadmap row: {key}")
        require(key not in tasks, f"Duplicate roadmap packet: {key}")
        require(state in STATES, f"Unknown roadmap state: {key} / {state}")
        deps = tuple(dict.fromkeys(re.findall(rf"\b{PACKET}\b", cells[1])))
        conditional = set()
        # A semicolon separates qualifications (e.g. N03 only for first boot).
        # Plain comma/slash lists are hard edges; prose-qualified lists are dotted.
        for clause in cells[1].split(";"):
            if re.sub(rf"{PACKET}|[,/\s]", "", clause):
                conditional.update(re.findall(rf"\b{PACKET}\b", clause))
        tasks[key] = Task(key, state, deps, frozenset(conditional), cells[1], section, STATES[state])
    require(tasks, "No roadmap packets found")
    for key, progress in annotations.items():
        require(key in tasks, f"Unknown annotated packet: {key}")
        require(tasks[key].state != "done", f"Finished packet marked partial: {key}")
        tasks[key] = replace(tasks[key], progress=progress)
    visited = set()

    def visit(key, ancestors):
        require(key in tasks, f"Undefined dependency: {key}")
        require(key not in ancestors, f"Dependency cycle: {key}")
        if key not in visited:
            for dependency in tasks[key].dependencies:
                visit(dependency, ancestors | {key})
            visited.add(key)

    for key in tasks:
        visit(key, set())
    return tasks


def queue_activity(text, tasks):
    """Read only active/review rows, never promote a completed subtask to done."""
    activity = {}
    running = []
    for section, cells, _header in table_rows(text):
        if section not in {"Running", "In review"}:
            continue
        if not cells or cells[0] in {"Packet", "Item"} or cells[0].startswith("---"):
            continue
        keys = re.findall(rf"\b{PACKET}\b", cells[1]) if section == "Running" and len(cells) > 1 else []
        subject_key = re.match(rf"^`?({PACKET})\b", cells[0])
        if subject_key:
            keys.append(subject_key[1])
        keys = tuple(dict.fromkeys(keys))
        for key in keys:
            require(key in tasks, f"Unknown active packet: {key}")
            require(tasks[key].state != "done", f"Finished packet still active: {key}")
            state = "review" if section == "In review" or re.search(
                r"\breview\b", cells[0], re.I) else "running"
            # Editing wins if the packet also has an older pending-review row.
            if activity.get(key) != "running":
                activity[key] = state
        if section == "Running":
            running.append((cells[0], keys))
    return activity, running


def slug(heading):
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def escape(label):
    return label.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def classes():
    return [
        f"    classDef {state} fill:{fill},stroke:{outline},color:#111827,stroke-width:2px;"
        for state, (fill, outline, _) in STYLES.items()
    ]


def node(key, title, state):
    return f'    {key}["{escape(title)}<br/>{STYLES[state][2]}"]:::{state}'


def graph(tasks, states, targets):
    """Every edge is emitted with its dependent, including external prerequisites."""
    targets = set(targets)
    visible = targets | {dep for key in targets for dep in tasks[key].dependencies}
    # Wide prerequisite fan-outs become unreadably small when Markdown scales
    # them to the page width. Let the largest diagrams scroll vertically instead.
    direction = "LR" if len(visible) > 16 else "TD"
    lines = ["```mermaid", f"flowchart {direction}"]
    for key in tasks:
        if key in visible:
            lines.append(node(key, f"{key} · {TITLES[key]}", states[key]))
    for key, task in tasks.items():
        if key in targets:
            for dep in task.dependencies:
                arrow = "-.->" if dep in task.conditional else "-->"
                lines.append(f"    {dep} {arrow} {key}")
    return "\n".join(lines + classes() + ["```"])


def aggregate(states):
    values = set(states)
    if values == {"finished"}:
        return "finished"
    if "running" in values:
        return "running"
    if "review" in values and values <= {"review", "finished"}:
        return "review"
    if values & {"finished", "partial", "review"}:
        return "partial"
    return "blocked" if "blocked" in values else "untouched"


def overview(states, parallel=False):
    keys = PARALLEL if parallel else tuple(key for key in STAGES if key not in PARALLEL)
    lines = ["```mermaid", "flowchart TD"]
    for key in keys:
        title, packets = STAGES[key]
        state = aggregate(states[p] for p in packets)
        lines.append(node(key, title, state))
    if not parallel:
        lines.extend(f"    {before} --> {after}" for before, after in OVERVIEW_EDGES)
    return "\n".join(lines + classes() + ["```"])


def render(roadmap, queue):
    tasks = parse_roadmap(roadmap)
    require(set(TITLES) == set(tasks),
            f"Update presentation titles: missing={sorted(set(tasks) - set(TITLES))}, "
            f"obsolete={sorted(set(TITLES) - set(tasks))}")
    stage_packets = [key for _, packets in STAGES.values() for key in packets]
    require(len(stage_packets) == len(set(stage_packets)) and set(stage_packets) == set(tasks),
            "Overview stages must cover each roadmap packet exactly once")
    activity, running = queue_activity(queue, tasks)
    states = {key: activity.get(key, task.progress) for key, task in tasks.items()}
    counts = Counter(states.values())
    fingerprint = hashlib.sha256((roadmap + "\0" + queue).encode()).hexdigest()[:12]
    lines = [
        "# Debra progress and dependencies", "",
        "<!-- Generated by tools/progress.py; edit the sources, not this page. -->", "",
        "**The destination:** an affordable, browser-configured Home Assistant voice/music",
        "device, with reliable setup, updates and recovery, plus sourced buying/build",
        "guidance. Full original Zero W support and validated enclosure variants remain",
        "separate engineering tracks, not claims established by the Pi 5 demo.", "",
        "For demonstrated device behaviour, prototype limits and what is **not yet",
        "validated**, see the [evidence summary](guides/current-status.md).", "",
        "This is a **tracked planning snapshot, not a live device/worker monitor**.",
        "Status comes from the [roadmap](roadmap.md) and [work queue](work-queue.md).",
        f"Source fingerprint: `{fingerprint}`. Regenerate after changing either source.", "",
        "## Colour key", "",
        "| Colour | Label | Meaning |",
        "| --- | --- | --- |",
        "| 🟩 Green | Finished | Whole packet accepted/integrated, not merely one successful subtask |",
        "| 🟦 Blue | In progress | An editing/implementation row is active in the work queue |",
        "| 🟪 Purple | In review | Deliverable awaits review, or its acceptance review is active |",
        "| 🟨 Amber | Partial | Prototype, limited evidence or incomplete scope; not accepted |",
        "| 🟥 Red | Blocked | Roadmap prerequisites remain open; unrelated exploration can continue |",
        "| ⬜ Grey | Untouched | Roadmap says ready, but no tracked work/progress is recorded |", "",
        "Labels accompany colours. **Maturity and dependency readiness are separate:**",
        "a partial/in-review packet can still have unmet prerequisites. The packet",
        "tables below retain both. Grey means no *recorded* progress, not proof no",
        "one has ever investigated it. Neither colour nor readiness grants device permission.", "",
        f"**{len(tasks)} roadmap packets:** " + " · ".join(
            f"{counts[state]} {style[2].lower()}" for state, style in STYLES.items()) + ".",
        "Counts are packets, **not a percentage complete**; packet sizes differ.", "",
        "## Product overview", "",
        "A simplified capability flow, not an execution order or a new set of gates.",
        "Overview colours roll up their packets: mixed completed/review/partial work",
        "is amber, active implementation blue, all finished green. Exact dependencies",
        "and per-packet status are in the expandable diagrams below.", "",
        overview(states), "",
        "### Parallel and deferred tracks", "",
        overview(states, parallel=True), "",
        "- **Zero W:** full voice/music support is a first-class goal; it is not",
        "  proven by another board and does not prevent accurately scoped other-board trials.",
        "- **Enclosures:** CAD → physical fit → thermal/acoustic validation, separately",
        "  from software gates. See the linked evidence for current validation limits.",
        "- **Agent permissions:** closed self-selection dispatch is not a blanket",
        "  block on coordinator-assigned development.",
        "- **Rescue/media loss:** deferred; not a prerequisite for browser controls or",
        "  the current on-target file-restore milestone. Later release/failure packets",
        "  still name B05 where applicable.",
        "- Optional sensors/radios/network extras are [unapproved candidates](roadmap.md#optional-extras-unreviewed-candidates-not-approved),",
        "  not required product steps or supported features.", "",
        "## Recorded active work", "",
    ]
    if running:
        for title, keys in running:
            suffix = ", ".join(keys) if keys else "no roadmap packet linked"
            lines.append(f"- {title} — {suffix}.")
    else:
        lines.append("No active rows are recorded in the work queue.")
    lines += [
        "", "This is what the queue records, not a liveness check. See",
        "[review outcomes, queued work and named blockers](work-queue.md), including",
        "[facts still needed from James](work-queue.md#needs-james).", "",
        "## Detailed dependency diagrams", "",
        "**Arrow direction:** prerequisite → dependent. Solid arrows are unqualified",
        "roadmap prerequisites; dotted arrows carry a qualification (for example,",
        "\"before writes\" or \"for final onboarding\"). Read the original dependency",
        "text in each table; slashes without a qualification mean all named prerequisites.",
        "External prerequisite nodes are repeated for context; each packet's incoming",
        "edges appear in its own section. All roadmap packets, including WEB01–WEB10,",
        "are included, even though the dispatch catalog excludes the browser lane.",
        "The open-packet column checks packet IDs only; requirements written as prose",
        "(such as named-target recovery) remain in the original wording and are **not**",
        "evaluated by this tool. A dash does not mean those requirements passed.", "",
    ]
    sections = dict.fromkeys(task.section for task in tasks.values())
    for section in sections:
        group = [key for key, task in tasks.items() if task.section == section]
        lines += [
            "<details>", f"<summary>{section} ({len(group)} packets)</summary>", "",
            f"[Acceptance and evidence](roadmap.md#{slug(section)})", "",
            graph(tasks, states, group), "",
            "| Packet / step | Progress | Roadmap state | Prerequisites (original wording) | Open packet prerequisites |",
            "| --- | --- | --- | --- | --- |",
        ]
        for key in group:
            task = tasks[key]
            missing = [dep for dep in task.dependencies if tasks[dep].state != "done"]
            lines.append(
                f"| {key} · {TITLES[key]} | {STYLES[states[key]][2]} | {task.state} | "
                f"{task.dependency_text} | {', '.join(missing) or '—'} |")
        lines += ["", "</details>", ""]
    lines += [
        "## Keeping this maintained", "",
        "1. Update packet acceptance/state/evidence in [roadmap.md](roadmap.md).",
        "   Where limited work exists despite an open acceptance gate, update its",
        "   [visual progress annotation](roadmap.md#visual-progress-annotations) with",
        "   linked evidence/limits. Remove the annotation when the packet is accepted.",
        "2. Update execution/review rows in [work-queue.md](work-queue.md). In the",
        "   Running table, put roadmap IDs in **Item ids** (or start the subject with",
        "   its packet ID). Active review subjects must say **review**; other active",
        "   rows count as implementation. In-review subjects start with the packet ID",
        "   when they refer to a whole packet. Finishing a subtask never finishes its packet.",
        "3. From the repository root:", "",
        "   ```sh",
        "   python3 tools/progress.py",
        "   python3 tools/progress.py --check",
        "   python3 -B -m unittest discover -s tests -p 'test_progress.py' -v",
        "   ```", "",
        "The generator reads only those two tracked sources. It does not poll",
        "workers, infer completion from test counts, change claims, run hardware,",
        "or contact services. The offline test suite checks this page for drift.",
        "New packets need short presentation titles/overview placement in",
        "[the generator](../tools/progress.py); missing/unknown packets, dependency",
        "cycles and unsupported states fail rather than silently disappearing.", "",
        "A coordinator updates the sources and regenerates this view with each",
        "relevant progress/handoff change. Nothing updates unattended unless a",
        "separately configured process actually runs the command.", "",
    ]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on a stale/missing page; write nothing")
    args = parser.parse_args(argv)
    try:
        page = render((ROOT / "docs/roadmap.md").read_text(encoding="utf-8"),
                      (ROOT / "docs/work-queue.md").read_text(encoding="utf-8"))
        target = ROOT / OUTPUT
        if args.check:
            if not target.exists() or target.read_text(encoding="utf-8") != page:
                print(f"STALE {OUTPUT}; run python3 tools/progress.py", file=sys.stderr)
                return 1
            print(f"PASS {OUTPUT} matches the roadmap and work queue")
        else:
            target.write_text(page, encoding="utf-8")
            print(f"Updated {OUTPUT}")
    except (OSError, ValueError) as error:
        print(f"Progress error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
