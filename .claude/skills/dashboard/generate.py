#!/usr/bin/env python3
"""Shippable BOS Dashboard generator (P016).

Reads a BOS's markdown files and writes ONE self-contained `dashboard.html`
(all CSS/JS inlined, zero external dependencies, no server, no creds). The user
opens the file in a browser. It is a point-in-time SNAPSHOT — regenerate it
whenever you want the current picture (the `/dashboard` skill wraps this).

This is the *structural / Five-Focusing-Steps* view that every BOS user can
produce from their own files:
  - the system constraint + re-evaluation cadence (Step 1 + Step 5)
  - per-project S&T trees (Level 1 mini-dashboard + Level 2-n IO cards)
  - IO status roll-up (date-paced) + the headline verdict
  - the decision log + drag indicator
  - git / memory backup health (creds-free)

It deliberately does NOT include the live-metrics panels (social/YouTube/
payments) are intentionally out of scope — those need integrations,
credentials, and ingestion crons no two users share, and they are not derivable
from the markdown.

Architecture note (P016): this file is split into three sections that map to the
project's IOs:
  - READER  (IO1): markdown -> typed data model, degrades PER-FILE.
  - RENDERER (IO2): data model -> one inlined HTML string.
  - MAIN    (IO3 entry): CLI the skill calls.

HARD REQUIREMENT (IO1): a malformed project/IO file is skipped with a visible
warning, NEVER crashes the whole render. A divergent IO schema once took the
dashboard down for a whole team for ~9 days; this ships to people whose
files will be messier than the reference instance, so per-file tolerance is a
feature, not a nicety.

Usage:
    python3 generate.py                 # auto-detect BOS root, write <root>/dashboard.html
    python3 generate.py --root /path    # explicit BOS root
    python3 generate.py --out foo.html  # explicit output path
    python3 generate.py --print         # write file AND echo path

Dependencies: Python 3.8+ and PyYAML (`pip install pyyaml`). The OUTPUT html has
no dependencies at all.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    sys.stderr.write(
        "ERROR: PyYAML is required to generate the dashboard.\n"
        "Install it with:  pip install pyyaml\n"
        "(or: python3 -m pip install pyyaml)\n"
    )
    sys.exit(2)

import re


# =====================================================================
# ROOT DETECTION
# =====================================================================

def find_bos_root(start: Optional[Path] = None) -> Path:
    """Find the BOS root by walking up from `start` (default cwd) looking for a
    directory that holds CLAUDE.md and a projects/ folder. Falls back to cwd."""
    base = Path(start or Path.cwd()).resolve()
    for d in [base, *base.parents]:
        if (d / "CLAUDE.md").exists() and (d / "projects").is_dir():
            return d
    return base


# =====================================================================
# READER  (IO1) — markdown -> typed data model, degrades per-file
# =====================================================================

@dataclass
class IO:
    id: str
    name: str
    project: str
    step: str = ""
    criticality: str = "supporting"
    mode: str = "date-paced"
    status: str = "open"
    target_date: Optional[date] = None
    metrics: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    necessary_assumption: Optional[str] = None
    strategy: Optional[str] = None
    parallel_assumption: Optional[str] = None
    tactic: Optional[str] = None
    sufficiency_assumption: Optional[str] = None
    children: List["IO"] = field(default_factory=list)


@dataclass
class ProjectMeta:
    slug: str
    display_name: str
    p_number: Optional[str] = None
    goal: Optional[str] = None
    constraint_interaction: Optional[str] = None
    constraint_note: Optional[str] = None
    why: Optional[str] = None
    tactic: Optional[str] = None
    sufficiency_assumption: Optional[str] = None
    source_path: str = ""


@dataclass
class Project:
    meta: ProjectMeta
    tree: List[IO]


@dataclass
class ArchivedProject:
    slug: str
    display_name: str
    archived_date: Optional[date] = None
    summary: str = ""
    source_path: str = ""


@dataclass
class CadenceEntry:
    artifact: str
    last_reviewed: Optional[date]
    cadence: str
    notes: str = ""


@dataclass
class Constraint:
    statement: str
    source_file: str
    last_reviewed: Optional[date]
    cadence_table: List[CadenceEntry] = field(default_factory=list)


@dataclass
class Decision:
    date: date
    entry_type: str
    decision: str
    reasoning: str
    constraint_addressed: str
    is_constraint_aligned: bool
    context: str = ""


@dataclass
class GitStatus:
    repo_path: str
    remote_url: Optional[str] = None
    branch: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    last_commit_sha: Optional[str] = None
    last_commit_message: Optional[str] = None
    last_pushed_at: Optional[datetime] = None
    uncommitted_files: int = 0
    unpushed_commits: int = 0
    error: Optional[str] = None
    available: bool = True


@dataclass
class BosState:
    root: Path
    constraint: Constraint
    cloud_date: Optional[date]
    projects: List[Project]
    archived: List[ArchivedProject]
    decisions: List[Decision]
    git: GitStatus
    warnings: List[str] = field(default_factory=list)


_IOS_BLOCK_RE = re.compile(
    r"## IOs \(machine-readable\)[\s\S]*?```yaml\n([\s\S]*?)\n```",
    re.MULTILINE,
)
_ARCHIVED_FILENAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")
_CONSTRAINT_STATEMENT_RE = re.compile(
    r"## System Constraint \(Persistent\)\s*\n+\*\*([^*]+)\*\*",
)
_CADENCE_SECTION_RE = re.compile(
    r"## Re-Evaluation Cadence\s*\n([\s\S]*?)(?=\n## |\Z)",
)
_CLOUD_LAST_REVIEWED_RE = re.compile(r"\*\*Last reviewed:\s*(\d{4}-\d{2}-\d{2})\*\*")
_DECISION_LINE_RE = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2})\]\s+(DECISION|CORRECTION):\s*(.+)$",
    re.MULTILINE,
)
_SECTION_SPLIT_RE = re.compile(
    r"\s+\|\s+(?=REASONING:|CONSTRAINT ADDRESSED:|CONTEXT:)",
)
_DRAG_SECTION_RE = re.compile(
    r"## Drag This Week\s*\n(.*?)(?=\n## |\Z)",
    re.IGNORECASE | re.DOTALL,
)

_VALID_STATUSES = {"open", "in-progress", "done", "blocked", "deferred", "needs-update"}
_VALID_CRITICALITY = {"critical", "supporting", "parallel"}


def _slug_to_titlecase(slug: str) -> str:
    return " ".join(w.capitalize() for w in slug.split("-"))


def _parse_target_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def _parse_io_node(entry: dict, project_name: str) -> IO:
    """Parse one IO YAML node (and its children). Raises ValueError on a
    structurally invalid node so the caller can degrade the whole file."""
    # STRUCTURAL validation only — these are the failures that would otherwise
    # take the whole page down. Minor enum drift is tolerated and rendered
    # leniently (see below + compute_io_status), so one off-spec value never
    # costs the user a whole project.
    if not isinstance(entry, dict):
        raise ValueError(f"IO entry is not a mapping: {entry!r}")
    if "id" not in entry or "name" not in entry:
        raise ValueError(f"IO entry missing required id/name: {entry!r}")

    # Lenient on enums: keep an unknown status as-is (compute_io_status renders it
    # grey with a 'non-standard status' note); coerce unknown criticality to the
    # safe non-critical default.
    status = str(entry.get("status", "open"))
    criticality = entry.get("criticality", "supporting")
    if criticality not in _VALID_CRITICALITY:
        criticality = "supporting"

    children_raw = entry.get("children") or []
    if not isinstance(children_raw, list):
        raise ValueError(f"IO {entry.get('id')!r} children is not a list")
    children = [_parse_io_node(c, project_name) for c in children_raw]

    return IO(
        id=str(entry["id"]),
        name=str(entry["name"]),
        project=project_name,
        step=entry.get("step", "") or "",
        criticality=criticality,
        mode=entry.get("mode", "date-paced") or "date-paced",
        status=status,
        target_date=_parse_target_date(entry.get("target_date")),
        metrics=entry.get("metrics") or [],
        depends_on=entry.get("depends_on") or [],
        notes=entry.get("notes"),
        necessary_assumption=entry.get("necessary_assumption"),
        strategy=entry.get("strategy"),
        parallel_assumption=entry.get("parallel_assumption"),
        tactic=entry.get("tactic"),
        sufficiency_assumption=entry.get("sufficiency_assumption"),
        children=children,
    )


def parse_project_file(path: Path) -> Optional[Project]:
    """Parse one project file into (meta, IO tree). Returns None if the file has
    no IOs block at all. Raises on a malformed block so the walker can record a
    per-file warning and skip just that file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _IOS_BLOCK_RE.search(text)
    if not match:
        return None
    data = yaml.safe_load(match.group(1))  # may raise yaml.YAMLError -> caught upstream
    if not isinstance(data, dict):
        raise ValueError("IOs block did not parse to a mapping")

    slug = path.stem
    project_block = data.get("project") or {}
    if not isinstance(project_block, dict):
        raise ValueError("`project:` key is not a mapping")

    meta = ProjectMeta(
        slug=slug,
        display_name=project_block.get("display_name") or _slug_to_titlecase(slug),
        p_number=project_block.get("p_number"),
        goal=project_block.get("goal"),
        constraint_interaction=project_block.get("constraint_interaction"),
        constraint_note=project_block.get("constraint_note"),
        why=project_block.get("why"),
        tactic=project_block.get("tactic"),
        sufficiency_assumption=project_block.get("sufficiency_assumption"),
        source_path=str(path),
    )

    ios_raw = data.get("ios") or []
    if not isinstance(ios_raw, list):
        raise ValueError("`ios:` key is not a list")
    tree = [_parse_io_node(entry, slug) for entry in ios_raw]
    return Project(meta=meta, tree=tree)


def parse_archived_project(path: Path) -> Optional[ArchivedProject]:
    stem = path.stem
    match = _ARCHIVED_FILENAME_RE.match(stem)
    if match:
        date_str, slug = match.groups()
        try:
            archived_date: Optional[date] = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            archived_date = None
    else:
        slug = stem
        archived_date = None

    display_name = _slug_to_titlecase(slug)
    summary = ""
    text = path.read_text(encoding="utf-8", errors="replace")
    ios_match = _IOS_BLOCK_RE.search(text)
    if ios_match:
        data = yaml.safe_load(ios_match.group(1)) or {}
        project_block = data.get("project") or {} if isinstance(data, dict) else {}
        if isinstance(project_block, dict):
            if project_block.get("display_name"):
                display_name = project_block["display_name"]
            if project_block.get("archived_summary"):
                summary = str(project_block["archived_summary"]).strip()
            yaml_archived_date = _parse_target_date(project_block.get("archived_date"))
            if yaml_archived_date:
                archived_date = yaml_archived_date

    return ArchivedProject(
        slug=slug,
        display_name=display_name,
        archived_date=archived_date,
        summary=summary,
        source_path=str(path),
    )


def parse_constraint(constraints_path: Path) -> Constraint:
    if not constraints_path.exists():
        return Constraint(statement="", source_file=str(constraints_path), last_reviewed=None)
    text = constraints_path.read_text(encoding="utf-8", errors="replace")

    statement_match = _CONSTRAINT_STATEMENT_RE.search(text)
    statement = statement_match.group(1).strip() if statement_match else ""

    cadence_entries: List[CadenceEntry] = []
    constraint_last_reviewed: Optional[date] = None
    section_match = _CADENCE_SECTION_RE.search(text)
    if section_match:
        for line in section_match.group(1).splitlines():
            line = line.strip()
            if not line.startswith("|"):
                continue
            if line.startswith("|---") or line.startswith("| Artifact"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 3:
                continue
            artifact, last_str, cadence = cells[0], cells[1], cells[2]
            notes = cells[3] if len(cells) > 3 else ""
            try:
                last_date = datetime.strptime(last_str, "%Y-%m-%d").date()
            except ValueError:
                last_date = None
            cadence_entries.append(CadenceEntry(artifact, last_date, cadence, notes))
            if "Constraint statement" in artifact:
                constraint_last_reviewed = last_date

    return Constraint(
        statement=statement,
        source_file=str(constraints_path),
        last_reviewed=constraint_last_reviewed,
        cadence_table=cadence_entries,
    )


def parse_competing_cloud_review_date(path: Path) -> Optional[date]:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    match = _CLOUD_LAST_REVIEWED_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    except ValueError:
        return None


def parse_decisions(decisions_path: Path) -> List[Decision]:
    if not decisions_path.exists():
        return []
    text = decisions_path.read_text(encoding="utf-8", errors="replace")
    out: List[Decision] = []
    for match in _DECISION_LINE_RE.finditer(text):
        date_str, entry_type, rest = match.groups()
        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        parts = _SECTION_SPLIT_RE.split(rest)
        decision_text = parts[0].strip()
        reasoning = constraint_addressed = context = ""
        for part in parts[1:]:
            if part.startswith("REASONING:"):
                reasoning = part[len("REASONING:"):].strip()
            elif part.startswith("CONSTRAINT ADDRESSED:"):
                constraint_addressed = part[len("CONSTRAINT ADDRESSED:"):].strip()
            elif part.startswith("CONTEXT:"):
                context = part[len("CONTEXT:"):].strip()
        is_aligned = bool(constraint_addressed) and not constraint_addressed.lower().startswith("none")
        out.append(Decision(
            date=entry_date, entry_type=entry_type, decision=decision_text,
            reasoning=reasoning, constraint_addressed=constraint_addressed,
            is_constraint_aligned=is_aligned, context=context,
        ))
    return out


def parse_latest_weekly_drag(reviews_dir: Path) -> Optional[str]:
    if not reviews_dir.exists():
        return None
    candidates = []
    for p in reviews_dir.glob("*.md"):
        try:
            datetime.strptime(p.stem, "%Y-%m-%d")
            candidates.append(p)
        except ValueError:
            continue
    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stem)
    text = latest.read_text(encoding="utf-8", errors="replace")
    match = _DRAG_SECTION_RE.search(text)
    if not match:
        return None
    body = match.group(1).strip()
    cleaned_lines = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("*") and stripped.endswith("*") and stripped.count("*") >= 2:
            continue
        cleaned_lines.append(line)
    cleaned = "\n".join(cleaned_lines).strip()
    if cleaned in ("-", "- ", ""):
        return None
    return cleaned


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def parse_git_status(repo_path: Path) -> GitStatus:
    status = GitStatus(repo_path=str(repo_path))
    try:
        # Is this even a git repo? Degrade quietly if not.
        _git(repo_path, "rev-parse", "--is-inside-work-tree")
    except Exception as e:
        status.available = False
        status.error = str(e)
        return status
    try:
        try:
            status.remote_url = _git(repo_path, "remote", "get-url", "origin")
        except Exception:
            status.remote_url = None
        status.branch = _git(repo_path, "rev-parse", "--abbrev-ref", "HEAD")

        head_line = _git(repo_path, "log", "-1", "--format=%H%x09%ct%x09%s")
        sha, ct, *msg_parts = head_line.split("\t")
        status.last_commit_sha = sha[:8]
        status.last_commit_at = datetime.fromtimestamp(int(ct))
        status.last_commit_message = "\t".join(msg_parts) if msg_parts else ""

        try:
            upstream = _git(repo_path, "rev-parse", "--abbrev-ref", "@{upstream}")
            up_ct = _git(repo_path, "log", "-1", "--format=%ct", upstream)
            status.last_pushed_at = datetime.fromtimestamp(int(up_ct))
            unpushed = _git(repo_path, "rev-list", "--count", f"{upstream}..HEAD")
            status.unpushed_commits = int(unpushed)
        except Exception:
            pass

        porcelain = _git(repo_path, "status", "--porcelain")
        status.uncommitted_files = len([ln for ln in porcelain.splitlines() if ln.strip()])
    except Exception as e:
        status.error = str(e)
    return status


def read_bos(root: Path) -> BosState:
    """Build the full data model from a BOS root. Project files degrade
    individually: a malformed file becomes a warning, never an exception that
    takes the whole render down."""
    warnings: List[str] = []

    constraint = Constraint(statement="", source_file="", last_reviewed=None)
    try:
        constraint = parse_constraint(root / "context/constraints.md")
    except Exception as e:
        warnings.append(f"context/constraints.md: could not parse constraint ({e})")

    cloud_date = None
    try:
        cloud_date = parse_competing_cloud_review_date(root / "references/competing-clouds.md")
    except Exception as e:
        warnings.append(f"references/competing-clouds.md: {e}")

    # --- Projects: per-file degradation (the hard requirement) ---
    projects: List[Project] = []
    projects_dir = root / "projects"
    if projects_dir.is_dir():
        for path in sorted(projects_dir.rglob("*.md")):
            try:
                proj = parse_project_file(path)
            except (yaml.YAMLError, ValueError, KeyError, TypeError) as e:
                warnings.append(f"projects/{path.relative_to(projects_dir)}: skipped — {e}")
                continue
            except Exception as e:  # defensive: never let one file kill the page
                warnings.append(f"projects/{path.relative_to(projects_dir)}: skipped — unexpected: {e}")
                continue
            if proj:
                projects.append(proj)
    projects.sort(key=lambda p: p.meta.display_name.lower())

    # --- Archived projects (best-effort, per-file) ---
    archived: List[ArchivedProject] = []
    archives_dir = root / "archives"
    if archives_dir.is_dir():
        for path in sorted(archives_dir.rglob("*.md")):
            try:
                ap = parse_archived_project(path)
                if ap:
                    archived.append(ap)
            except Exception as e:
                warnings.append(f"archives/{path.name}: skipped — {e}")
        archived.sort(
            key=lambda a: (a.archived_date or date.min, a.display_name.lower()),
            reverse=True,
        )

    decisions: List[Decision] = []
    try:
        decisions = parse_decisions(root / "decisions/log.md")
    except Exception as e:
        warnings.append(f"decisions/log.md: {e}")

    git = parse_git_status(root)

    state = BosState(
        root=root, constraint=constraint, cloud_date=cloud_date,
        projects=projects, archived=archived, decisions=decisions,
        git=git, warnings=warnings,
    )
    # Attach the self-reported drag onto the state via a transient attr.
    try:
        state._drag_self = parse_latest_weekly_drag(root / "reviews/weekly")  # type: ignore[attr-defined]
    except Exception:
        state._drag_self = None  # type: ignore[attr-defined]
    return state


# =====================================================================
# STATUS / VERDICT (ported from verdict.py — date-paced only)
# =====================================================================

GREEN, YELLOW, RED, GREY = "green", "yellow", "red", "grey"
DUE_SOON_DAYS = 7
OVERDUE_RED_DAYS = 14
OPEN_STATUSES = {"open", "in-progress", "blocked", "needs-update"}
CLOSED_STATUSES = {"done", "deferred"}
_COLOR_PRIORITY = {RED: 3, YELLOW: 2, GREEN: 1, GREY: 0}


@dataclass
class IOStatus:
    io: IO
    color: str
    reason: str


def compute_io_status(io: IO, today: Optional[date] = None) -> IOStatus:
    today = today or date.today()
    if io.status == "done":
        return IOStatus(io, GREEN, "done")
    if io.status == "blocked":
        return IOStatus(io, RED, "blocked")
    if io.status == "deferred":
        return IOStatus(io, GREY, "deferred")
    if io.status == "needs-update":
        return IOStatus(io, GREY, "status needs update")
    if io.status not in _VALID_STATUSES:
        # Off-spec status value — render but don't guess a color.
        return IOStatus(io, GREY, f"non-standard status: {io.status}")

    if io.mode == "metric-driven":
        # Live metric data is not part of the static, creds-free dashboard.
        return IOStatus(io, GREY, "metric-driven — live data not in static view")

    # date-paced
    if io.target_date is None:
        return IOStatus(io, GREY, "no target date")
    days_to_target = (io.target_date - today).days
    if days_to_target >= DUE_SOON_DAYS:
        return IOStatus(io, GREEN, f"on pace ({days_to_target}d to target)")
    if days_to_target >= 0:
        return IOStatus(io, YELLOW, f"due in {days_to_target}d")
    overdue = -days_to_target
    if overdue <= OVERDUE_RED_DAYS:
        return IOStatus(io, YELLOW, f"{overdue}d past target")
    return IOStatus(io, RED, f"{overdue}d past target")


def flatten_ios(ios: List[IO]) -> List[IO]:
    out: List[IO] = []
    for io in ios:
        out.append(io)
        out.extend(flatten_ios(io.children))
    return out


def compute_verdict(io_statuses: List[IOStatus]) -> Tuple[str, str]:
    actionable = [s for s in io_statuses if s.color != GREY]
    if not actionable:
        return GREY, "no actionable IOs — everything is awaiting signal"
    critical = [s for s in actionable if s.io.criticality == "critical"]
    crit_red = [s for s in critical if s.color == RED]
    if crit_red:
        names = ", ".join(s.io.id for s in crit_red)
        return RED, f"{len(crit_red)} critical IO red ({names})"
    crit_yellow = [s for s in critical if s.color == YELLOW]
    if crit_yellow:
        names = ", ".join(s.io.id for s in crit_yellow)
        return YELLOW, f"{len(crit_yellow)} critical IO yellow ({names})"
    other_red = [s for s in actionable if s.color == RED]
    other_yellow = [s for s in actionable if s.color == YELLOW]
    if other_red:
        return YELLOW, f"{len(other_red)} non-critical IO red"
    if other_yellow:
        return YELLOW, f"{len(other_yellow)} IO yellow"
    return GREEN, f"all {len(actionable)} actionable IOs green"


@dataclass
class DragSignal:
    decisions_last_4w: int
    off_constraint_count: int
    self_reported: Optional[str] = None


def compute_drag(decisions: List[Decision], today: Optional[date] = None,
                 self_reported: Optional[str] = None) -> DragSignal:
    today = today or date.today()
    four_weeks_ago = today - timedelta(days=28)
    recent = [d for d in decisions if d.date >= four_weeks_ago]
    off = sum(1 for d in recent if not d.is_constraint_aligned)
    return DragSignal(len(recent), off, self_reported)


# ---------- Priority selection (the "big-ticket items" rubric) ----------
# Ranks the few open IOs that most move the user's bottleneck, using ONLY the
# existing TOC signals already on every IO: whether its project acts on the
# constraint (exploit/subordinate/elevate), its criticality, and its date-paced
# urgency. No new scoring model — this just surfaces the top of what the system
# already knows.

_URGENCY_RANK = {RED: 3, YELLOW: 2, GREEN: 1, GREY: 0}


@dataclass
class PriorityItem:
    io: IO
    meta: ProjectMeta
    color: str
    step_label: str   # "Resolve" | "Elevate" | "Unscoped"
    why: str
    score: tuple


def _io_has_open_child(io: IO) -> bool:
    return any(c.status in OPEN_STATUSES for c in io.children)


def _step_label_for(ci: Optional[str]) -> str:
    if ci in ("exploit", "subordinate"):
        return "Resolve"
    if ci == "elevate":
        return "Elevate"
    return "Unscoped"


def _priority_why(io: IO, ci: Optional[str], today: date) -> str:
    crit = "Critical" if io.criticality == "critical" else io.criticality.capitalize()
    if io.target_date is None:
        urg = "no target date"
    else:
        days = (io.target_date - today).days
        if days < 0:
            urg = f"{-days}d overdue"
        elif days == 0:
            urg = "due today"
        else:
            urg = f"due in {days}d"
    step = {
        "elevate": "breaks your bottleneck (elevate)",
        "exploit": "gets more from your bottleneck (exploit)",
        "subordinate": "protects your bottleneck (subordinate)",
    }.get(ci or "", "not yet tied to your bottleneck")
    return f"{crit} · {urg} · {step}"


def select_priority_ios(projects: List[Project], today: Optional[date] = None,
                        n: int = 4) -> List[PriorityItem]:
    """Top-N open IOs that most move the bottleneck. Candidate pool = the live
    frontier (open IOs with no open children), so we surface the concrete next
    objective, not a parent whose child is the real action. Constraint-tagged
    IOs rise first; the pool is filled from untagged IOs if fewer than N exist."""
    today = today or date.today()
    items: List[PriorityItem] = []
    for proj in projects:
        ci = proj.meta.constraint_interaction
        for io in flatten_ios(proj.tree):
            if io.status not in OPEN_STATUSES:
                continue
            if _io_has_open_child(io):
                continue
            st = compute_io_status(io, today)
            constraint_bonus = 1 if ci else 0
            crit = 2 if io.criticality == "critical" else 1
            urg = _URGENCY_RANK.get(st.color, 0)
            days = (io.target_date - today).days if io.target_date else 10 ** 6
            score = (constraint_bonus, crit, urg, -days)
            items.append(PriorityItem(
                io=io, meta=proj.meta, color=st.color,
                step_label=_step_label_for(ci),
                why=_priority_why(io, ci, today), score=score,
            ))
    items.sort(key=lambda p: p.score, reverse=True)
    return items[:n]


# =====================================================================
# RENDERER  (IO2) — data model -> one inlined HTML string
# =====================================================================

def _flow_text(value: Optional[str]) -> str:
    if not value:
        return ""
    return " ".join(line.strip() for line in str(value).strip().splitlines() if line.strip())


def _project_number(meta: ProjectMeta) -> str:
    return meta.p_number or meta.slug


def render_headline(color: str, reason: str, drag: DragSignal, constraint: Constraint) -> str:
    color_label = {GREEN: "GREEN", YELLOW: "YELLOW", RED: "RED", GREY: "GREY"}[color]
    drag_line = (
        f"{drag.decisions_last_4w} decisions in last 4 weeks, "
        f"{drag.off_constraint_count} flagged off-constraint"
    )
    if drag.self_reported:
        drag_line += f" &middot; self-reported: {escape(drag.self_reported)}"
    return f"""
<div class="headline {color}">
  <div class="dot"></div>
  <div class="headline-body">
    <div class="headline-label">Constraint health</div>
    <div class="headline-status">{color_label}</div>
    <div class="headline-reason">{escape(reason)}</div>
    <div class="muted small">{drag_line}</div>
  </div>
</div>
"""


def render_bottleneck_header(constraint: Constraint, verdict_color: str,
                             verdict_reason: str, cloud_date) -> str:
    """The top of the shipped view: the user's bottleneck in plain words + a
    health badge. Merges Step-1 Identify with the overall verdict."""
    today = date.today()
    health_label = {GREEN: "HEALTHY", YELLOW: "NEEDS ATTENTION",
                    RED: "AT RISK", GREY: "NO SIGNAL"}[verdict_color]

    if not constraint.statement:
        statement_html = (
            '<div class="bn-statement bn-statement-missing">'
            'No bottleneck defined yet &mdash; run the diagnostic (Step 1: Identify) '
            'to name the one thing limiting your business.</div>'
        )
        freshness = ""
    else:
        statement_html = f'<div class="bn-statement">{escape(constraint.statement)}</div>'
        if constraint.last_reviewed:
            age = (today - constraint.last_reviewed).days
            freshness = f'<div class="muted small bn-freshness">Last re-affirmed {age}d ago &middot; review quarterly.</div>'
        else:
            freshness = '<div class="muted small bn-freshness">Not yet reviewed &middot; review quarterly.</div>'

    return f"""
<div class="bottleneck {verdict_color}">
  <div class="bn-top">
    <div class="bn-label">Your Bottleneck</div>
    <div class="bn-badge bn-badge-{verdict_color}">{health_label}</div>
  </div>
  {statement_html}
  <div class="bn-reason muted small">Bottleneck health: {escape(verdict_reason)}.</div>
  {freshness}
</div>
"""


def render_priority_panel(items: List[PriorityItem]) -> str:
    """The 3-4 big-ticket items that move the bottleneck right now."""
    if not items:
        body = (
            '<div class="muted small prio-empty">'
            "No open objectives right now &mdash; everything's done or deferred. "
            "Re-run the diagnostic to find the next bottleneck, or open a project "
            "below to add the next intermediate objective.</div>"
        )
        return (f'<div class="panel prio-panel"><div class="panel-title">'
                f'What Moves Your Bottleneck Now</div>{body}</div>')

    today = date.today()
    cards = []
    for p in items:
        chip_cls = {"Resolve": "chip-resolve", "Elevate": "chip-elevate"}.get(
            p.step_label, "chip-unscoped")
        # target / countdown
        if p.io.target_date:
            days = (p.io.target_date - today).days
            if days < 0:
                cd = f'<span class="countdown overdue">{-days}d past</span>'
            elif days == 0:
                cd = '<span class="countdown due">today</span>'
            elif days <= 7:
                cd = f'<span class="countdown due">in {days}d</span>'
            else:
                cd = f'<span class="countdown">in {days}d</span>'
            target_html = (f'<span class="prio-target">{p.io.target_date.isoformat()} {cd}</span>')
        else:
            target_html = '<span class="prio-target muted small">no target date</span>'

        cards.append(f"""
<div class="prio-card prio-{p.color}">
  <div class="prio-head">
    <span class="pip {p.color} pip-lg"></span>
    <span class="prio-chip {chip_cls}">{escape(p.step_label)}</span>
    <span class="prio-name">{escape(p.io.name)}</span>
  </div>
  <div class="prio-meta">
    <a class="prio-project" href="#proj-{escape(p.meta.slug)}">{escape(p.meta.display_name)}</a>
    {target_html}
  </div>
  <div class="prio-why muted small">{escape(p.why)}</div>
</div>""")

    return f"""
<div class="panel prio-panel">
  <div class="panel-title">What Moves Your Bottleneck Now</div>
  <div class="muted small" style="margin-bottom:1rem">
    The {len(items)} open objective{'s' if len(items) != 1 else ''} that most move your
    bottleneck right now &mdash; ranked by whether they act on it, how critical they are,
    and how soon they're due. <strong>Resolve</strong> = get more from / protect the
    bottleneck; <strong>Elevate</strong> = break it.
  </div>
  <div class="prio-list">{"".join(cards)}</div>
</div>
"""


def _project_attention_score(statuses: List[IOStatus]) -> tuple:
    if not statuses:
        return (0, 0, 0, 0)
    crit_red = sum(1 for s in statuses if s.color == RED and s.io.criticality == "critical")
    crit_yellow = sum(1 for s in statuses if s.color == YELLOW and s.io.criticality == "critical")
    other_red = sum(1 for s in statuses if s.color == RED and s.io.criticality != "critical")
    other_yellow = sum(1 for s in statuses if s.color == YELLOW and s.io.criticality != "critical")
    return (crit_red, crit_yellow, other_red, other_yellow)


def _format_io_target_phrase(s: IOStatus, today: date) -> str:
    if not s.io.target_date:
        return ""
    days = (s.io.target_date - today).days
    if days < 0:
        return f" (target {s.io.target_date.isoformat()}, {-days}d past)"
    if days == 0:
        return f" (target {s.io.target_date.isoformat()}, due today)"
    return f" (target {s.io.target_date.isoformat()}, {days}d out)"


def _build_step_reason(statuses: List[IOStatus], verdict_color: str) -> str:
    today = date.today()
    red = sorted([s for s in statuses if s.color == RED],
                 key=lambda s: (s.io.criticality != "critical", s.io.target_date or date.max))
    yellow = sorted([s for s in statuses if s.color == YELLOW],
                    key=lambda s: (s.io.criticality != "critical", s.io.target_date or date.max))
    in_progress = [s for s in statuses if s.io.status == "in-progress"]
    if verdict_color == RED and red:
        worst, n = red[0], len(red)
        return (f"{n} IO{'s' if n != 1 else ''} in red, led by "
                f"<em>{escape(worst.io.name)}</em>{_format_io_target_phrase(worst, today)}. "
                f"Unblock or replan before the slip compounds.")
    if verdict_color == YELLOW and yellow:
        worst, n = yellow[0], len(yellow)
        return (f"{n} IO{'s' if n != 1 else ''} in yellow, led by "
                f"<em>{escape(worst.io.name)}</em>{_format_io_target_phrase(worst, today)}. "
                f"Tighten the loop while there's still runway.")
    if verdict_color == GREEN:
        if in_progress:
            return (f"all actionable IOs green; {len(in_progress)} in progress. "
                    f"Sustain pace — no intervention needed.")
        return "all actionable IOs green. Sustain pace — no intervention needed."
    if verdict_color == GREY:
        return ("all IOs are awaiting signal (no target dates set). "
                "Set target dates so this project can be reasoned about.")
    return "status unclear; inspect the project section for detail."


def _render_step1(constraint: Constraint, cloud_date) -> str:
    today = date.today()
    age_str, age_color = "never reviewed", "red"
    if constraint.last_reviewed:
        age = (today - constraint.last_reviewed).days
        age_color = "green" if age <= 90 else "yellow" if age <= 120 else "red"
        age_str = f"last re-affirmed {age}d ago"
    cloud_str = ""
    if cloud_date:
        cloud_str = f" Competing cloud last reviewed {(today - cloud_date).days}d ago."
    statement = constraint.statement or "No system constraint recorded in context/constraints.md."
    return f"""
<div class="step step-{age_color}">
  <div class="step-head"><span class="step-num">1</span> IDENTIFY</div>
  <div class="step-body">
    <div class="constraint-statement">{escape(statement)}</div>
    <div class="step-analysis step-analysis-{age_color}">
      {escape(age_str)}.{escape(cloud_str)} Quarterly cadence per
      <code>context/constraints.md</code>.
    </div>
  </div>
</div>"""


def _render_step_analysis(step_num, step_name, step_key, step_description, candidates) -> str:
    if not candidates:
        return f"""
<div class="step step-grey">
  <div class="step-head"><span class="step-num">{step_num}</span> {step_name}</div>
  <div class="step-body">
    <div class="muted small">{escape(step_description)}</div>
    <div class="step-analysis step-analysis-grey">
      No project currently tagged for {step_key}. Add
      <code>constraint_interaction: {step_key}</code> to a project's
      <code>project:</code> block to surface attention analysis here.
    </div>
  </div>
</div>"""
    ranked = sorted(candidates,
                    key=lambda c: (_COLOR_PRIORITY[c[2]], _project_attention_score(c[1])),
                    reverse=True)
    primary_meta, primary_statuses, primary_color, _ = ranked[0]
    reason_html = _build_step_reason(primary_statuses, primary_color)
    others_html = ""
    if len(ranked) > 1:
        names = ", ".join(
            f'<a href="#proj-{escape(m.slug)}">{escape(m.display_name)}</a>'
            f' <span class="pip {c}"></span>'
            for m, _, c, _ in ranked[1:]
        )
        others_html = f'<div class="muted small step-others">Also {step_key}: {names}.</div>'
    return f"""
<div class="step step-{primary_color}">
  <div class="step-head">
    <span class="step-num">{step_num}</span> {step_name}
    <span class="step-count muted small">({len(candidates)} project{"s" if len(candidates) != 1 else ""})</span>
  </div>
  <div class="step-body">
    <div class="muted small">{escape(step_description)}</div>
    <div class="step-analysis step-analysis-{primary_color}">
      Right now, <a href="#proj-{escape(primary_meta.slug)}"><strong>{escape(primary_meta.display_name)}</strong></a>
      needs the most attention to {step_key} &mdash; {reason_html}
    </div>
    {others_html}
  </div>
</div>"""


def _render_step5(constraint, cloud_date, io_statuses, drag) -> str:
    today = date.today()
    actionable = [s for s in io_statuses if s.color != GREY]
    total = len(actionable)
    red = sum(1 for s in actionable if s.color == RED)
    yellow = sum(1 for s in actionable if s.color == YELLOW)
    green = sum(1 for s in actionable if s.color == GREEN)
    done = sum(1 for s in io_statuses if s.io.status == "done")
    in_progress = sum(1 for s in io_statuses if s.io.status == "in-progress")
    open_count = sum(1 for s in io_statuses if s.io.status == "open")
    cloud_age = (today - cloud_date).days if cloud_date else None

    rec_color = "green"
    if total == 0:
        rec_color = "grey"
        headline = "No actionable signal yet."
        body = ("Most IOs are awaiting target dates. Before forward-looking analysis is "
                "useful, set target dates on date-paced IOs.")
    elif red > 0 and (red / total) >= 0.20:
        rec_color = "red"
        headline = "Stay in execution — too many red IOs to widen focus."
        body = (f"{red} of {total} actionable IOs are red ({red * 100 // total}%). "
                "Forward analysis won't pay until the current red items unblock. "
                "Triage the reds, then revisit.")
    elif (red + yellow) > 0 and ((red + yellow) / total) >= 0.40:
        rec_color = "yellow"
        headline = "Focus on completing what we have."
        body = (f"{red + yellow} of {total} actionable IOs are amber/red — execution still "
                "dominates. Hold the current Five Focusing Steps posture.")
    elif drag.off_constraint_count >= 3:
        rec_color = "yellow"
        headline = "Audit subordination — drift detected in the decision log."
        body = (f"{drag.off_constraint_count} of the last {drag.decisions_last_4w} logged "
                "decisions fell outside the constraint. Review the off-constraint entries "
                "before re-running the diagnostic.")
    elif cloud_age is not None and cloud_age > 90:
        rec_color = "yellow"
        headline = "Time to re-run the competing-cloud diagnostic."
        body = (f"Competing cloud was last reviewed {cloud_age}d ago (cadence: quarterly). "
                "Execution is green, which is when re-evaluation is cheapest.")
    elif done >= 5 and (done / max(len(io_statuses), 1)) >= 0.30:
        rec_color = "green"
        headline = "Ready to re-analyze bottlenecks (focus on Step 1)."
        body = (f"{done} IOs complete and execution is green ({green} of {total} actionable). "
                "Re-run the CRT and Five Focusing Steps to find where the next constraint lives.")
    elif in_progress >= 3 and yellow == 0 and red == 0:
        rec_color = "green"
        headline = "Stay focused on completing current work."
        body = (f"{in_progress} IOs in progress, all actionable signal green. Healthy "
                "execution mode — no need to widen the lens.")
    else:
        rec_color = "green"
        headline = "Hold posture — no signal to widen or narrow focus."
        body = (f"{green} green / {yellow} yellow / {red} red across {total} actionable IOs. "
                "Continue the current Exploit/Subordinate/Elevate posture.")

    open_breakdown = (
        f'<div class="muted small step-others">Snapshot: {done} done &middot; '
        f'{in_progress} in progress &middot; {open_count} open &middot; '
        f'{red + yellow} amber/red</div>'
    )
    return f"""
<div class="step step-{rec_color}">
  <div class="step-head"><span class="step-num">5</span> RE-EVALUATE</div>
  <div class="step-body">
    <div class="muted small">Audit the posture. Decide whether to keep executing or widen the lens.</div>
    <div class="step-analysis step-analysis-{rec_color}">
      <strong>{escape(headline)}</strong> {escape(body)}
    </div>
    {open_breakdown}
  </div>
</div>"""


def render_five_steps(constraint, cloud_date, io_statuses, projects, drag) -> str:
    by_project: Dict[str, List[IOStatus]] = {}
    for s in io_statuses:
        by_project.setdefault(s.io.project, []).append(s)
    by_step: Dict[str, List[tuple]] = {}
    for proj in projects:
        ci = proj.meta.constraint_interaction
        if not ci:
            continue
        statuses = by_project.get(proj.meta.slug, [])
        v_color, v_reason = compute_verdict(statuses)
        by_step.setdefault(ci, []).append((proj.meta, statuses, v_color, v_reason))
    return f"""
<div class="panel">
  <div class="panel-title">The Five Focusing Steps</div>
  {_render_step1(constraint, cloud_date)}
  {_render_step_analysis(2, "EXPLOIT", "exploit",
      "Get more business throughput per existing work hour.", by_step.get("exploit", []))}
  {_render_step_analysis(3, "SUBORDINATE", "subordinate",
      "Align other work to respect the time boundary.", by_step.get("subordinate", []))}
  {_render_step_analysis(4, "ELEVATE", "elevate",
      "Reduce total time required to produce business value.", by_step.get("elevate", []))}
  {_render_step5(constraint, cloud_date, io_statuses, drag)}
</div>
"""


def render_cadence_panel(constraint: Constraint) -> str:
    today = date.today()
    rows = []
    for c in constraint.cadence_table:
        if c.last_reviewed is None:
            when = '<span class="overdue">NEVER</span>'
        else:
            when = f"{(today - c.last_reviewed).days}d ago"
        rows.append(
            f'<div class="cadence-row"><span class="cadence-artifact">{escape(c.artifact)}</span>'
            f'<span class="muted small">{escape(c.cadence)}</span>'
            f'<span class="cadence-when">{when}</span></div>'
        )
    body = "".join(rows) or '<div class="muted small">no cadence entries</div>'
    return f'<div class="panel"><div class="panel-title">Re-Evaluation Cadence</div>{body}</div>'


def _io_field(label: str, value: Optional[str]) -> str:
    flat = _flow_text(value)
    if not flat:
        return ""
    return (f'<div class="io-field"><div class="io-field-label">{escape(label)}</div>'
            f'<div class="io-field-content">{escape(flat)}</div></div>')


def _render_io_card(s: IOStatus, card_id: str) -> str:
    today = date.today()
    is_critical = s.io.criticality == "critical"
    tag_label = "Critical" if is_critical else "Non-Critical"
    tag_class = "tag-critical" if is_critical else "tag-non-critical"

    target_html = ""
    if s.io.target_date:
        days = (s.io.target_date - today).days
        if s.io.status in ("done", "deferred"):
            countdown = ""
        elif days < 0:
            countdown = f' <span class="countdown overdue">{-days}d past</span>'
        elif days == 0:
            countdown = ' <span class="countdown due">today</span>'
        elif days <= 7:
            countdown = f' <span class="countdown due">in {days}d</span>'
        else:
            countdown = f' <span class="countdown">in {days}d</span>'
        target_html = (
            f'<div class="io-target"><span class="io-target-label">Target</span> '
            f'<span class="io-target-date">{s.io.target_date.isoformat()}</span>{countdown}</div>'
        )

    field_blocks = [
        _io_field("Necessary Assumption", s.io.necessary_assumption),
        _io_field("Strategy", s.io.strategy),
        _io_field("Parallel Assumption", s.io.parallel_assumption),
        _io_field("Tactic", s.io.tactic or s.io.notes),
    ]
    if s.io.sufficiency_assumption:
        field_blocks.append(_io_field("Sufficiency Assumption", s.io.sufficiency_assumption))
    elif not s.io.children:
        field_blocks.append(
            '<div class="io-field io-field-leaf"><div class="io-field-label">Sufficiency Assumption</div>'
            '<div class="io-field-content muted small">Leaf node &mdash; no sub-objectives below.</div></div>'
        )

    deps_html = ""
    if s.io.depends_on:
        deps = ", ".join(escape(str(d)) for d in s.io.depends_on)
        deps_html = (f'<div class="io-deps muted small"><span class="io-deps-label">Depends on</span> {deps}</div>')

    return f"""
<div class="io-card io-card-{s.color}">
  <div class="io-card-head">
    <span class="pip {s.color} pip-lg"></span>
    <span class="io-number copy-id" data-copy="{escape(card_id)}" title="Copy {escape(card_id)}">{escape(card_id)}</span>
    <span class="io-card-name">{escape(s.io.name)}</span>
    <span class="crit-tag {tag_class}">{tag_label}</span>
  </div>
  {"".join(field_blocks)}
  {target_html}
  {deps_html}
</div>"""


def _render_io_subtree(io: IO, card_id: str, depth: int) -> str:
    status = compute_io_status(io)
    card_html = _render_io_card(status, card_id)
    if io.children:
        child_cards = "".join(
            _render_io_subtree(c, f"{card_id} | L{depth+1}.{i}", depth + 1)
            for i, c in enumerate(io.children, start=1)
        )
        card_html += f'<div class="io-children">{child_cards}</div>'
    return card_html


def render_io_tree(project_tree: List[IO], project_num: str) -> str:
    # Exhaustive partition: only explicitly-closed statuses go to Closed; anything
    # else (including off-spec/unknown statuses) stays visible in Open so no IO is
    # ever silently dropped from the tree.
    closed_items = [(i, io) for i, io in enumerate(project_tree, start=1) if io.status in CLOSED_STATUSES]
    open_items = [(i, io) for i, io in enumerate(project_tree, start=1) if io.status not in CLOSED_STATUSES]

    sections = []
    if open_items:
        cards = "".join(_render_io_subtree(io, f"{project_num} | L2.{idx}", depth=2)
                        for idx, io in open_items)
        sections.append(f"""
<div class="io-section">
  <div class="io-section-title">Open <span class="muted small">({len(open_items)})</span></div>
  <div class="io-list">{cards}</div>
</div>""")
    else:
        sections.append("""
<div class="io-section">
  <div class="io-section-title">Open <span class="muted small">(0)</span></div>
  <div class="muted small io-empty">No open IOs &mdash; everything is done or deferred.</div>
</div>""")

    if closed_items:
        cards = "".join(_render_io_subtree(io, f"{project_num} | L2.{idx}", depth=2)
                        for idx, io in closed_items)
        sections.append(f"""
<div class="io-section io-section-closed">
  <div class="io-section-title">Closed <span class="muted small">({len(closed_items)})</span></div>
  <div class="io-list">{cards}</div>
</div>""")

    return f"""
<div class="panel">
  <div class="panel-title">Intermediate Objectives &mdash; S&amp;T Tree (Level 2 &mdash; n)</div>
  <div class="muted small" style="margin-bottom:1rem">
    Click any card identifier (e.g., <code>{escape(project_num)} | L2.1</code>) to copy it.
  </div>
  {"".join(sections)}
</div>
"""


_STEP_LABEL = {
    "exploit": ("Exploit", "Get more business throughput per existing work hour."),
    "subordinate": ("Subordinate", "Align other work to respect the time boundary."),
    "elevate": ("Elevate", "Reduce total time required to produce business value."),
}


def _level1_field(label: str, value: Optional[str], missing_msg: str) -> str:
    flat = _flow_text(value)
    if flat:
        return (f'<div class="l1-field"><div class="l1-field-label">{escape(label)}</div>'
                f'<div class="l1-field-content">{escape(flat)}</div></div>')
    return (f'<div class="l1-field l1-field-missing"><div class="l1-field-label">{escape(label)}</div>'
            f'<div class="l1-field-content">{escape(missing_msg)}</div></div>')


def render_project_mini_dashboard(meta: ProjectMeta, io_statuses: List[IOStatus], project_num: str) -> str:
    today = date.today()
    verdict_color, verdict_reason = compute_verdict(io_statuses)
    verdict_label = {GREEN: "GREEN", YELLOW: "YELLOW", RED: "RED", GREY: "GREY"}[verdict_color]

    status_counts: Dict[str, int] = {}
    for s in io_statuses:
        status_counts[s.io.status] = status_counts.get(s.io.status, 0) + 1
    status_order = ["in-progress", "open", "blocked", "needs-update", "done", "deferred"]
    status_chips = "".join(
        f'<span class="status-chip status-{escape(st)}">{status_counts[st]} {escape(st)}</span>'
        for st in status_order if status_counts.get(st)
    )

    upcoming = [s for s in io_statuses if s.io.target_date and s.io.status not in ("done", "deferred")]
    if upcoming:
        nxt = min(upcoming, key=lambda s: s.io.target_date)
        days = (nxt.io.target_date - today).days
        if days < 0:
            countdown = f'<span class="countdown overdue">{-days}d past</span>'
        elif days == 0:
            countdown = '<span class="countdown due">today</span>'
        else:
            countdown = f'<span class="countdown">in {days}d</span>'
        next_target_html = (
            f'<div class="mini-target"><span class="mini-target-date">{nxt.io.target_date.isoformat()}</span> '
            f'{countdown} &middot; <span class="mini-target-io">{escape(nxt.io.name)}</span></div>'
        )
    else:
        next_target_html = '<div class="mini-target muted small">no upcoming target dates</div>'

    purpose_html = _level1_field("Purpose", meta.goal,
        "Purpose not yet defined. What does success look like for this project?")
    why_html = _level1_field("Why (Necessary Assumption)", meta.why or meta.constraint_note,
        "Why not yet captured. What makes this initiative necessary right now?")
    tactic_html = _level1_field("Tactic (Method)", meta.tactic,
        "Tactic not yet captured. What method achieves the purpose at the project level?")
    sa_html = _level1_field("Sufficiency Assumption", meta.sufficiency_assumption,
        "Sufficiency Assumption not yet captured. Why are the IOs below needed?")

    if meta.constraint_interaction:
        ci = meta.constraint_interaction
        step_label, step_desc = _STEP_LABEL.get(ci, (ci.title(), ""))
        ci_html = (f'<div class="mini-ci"><span class="mini-ci-label">Constraint Interaction</span>'
                   f'<span class="step-badge step-{escape(ci)}">{escape(step_label)}</span>')
        if step_desc:
            ci_html += f' <span class="muted small">{escape(step_desc)}</span>'
        ci_html += '</div>'
    else:
        ci_html = ('<div class="mini-ci"><span class="mini-ci-label">Constraint Interaction</span>'
                   '<span class="muted small">Not tagged. Add <code>constraint_interaction: '
                   'exploit | subordinate | elevate</code>.</span></div>')

    return f"""
<div class="panel project-mini">
  <div class="project-mini-head">
    <div class="project-mini-titlebox">
      <div class="project-mini-pnum">
        <span class="copy-id" data-copy="{escape(project_num)}" title="Copy {escape(project_num)}">{escape(project_num)}</span>
      </div>
      <div class="project-mini-title">{escape(meta.display_name)}</div>
    </div>
    <div class="verdict-badge verdict-{verdict_color}">{verdict_label}</div>
  </div>
  <div class="l1-section-label">Level 1 &mdash; Viable Vision</div>
  {purpose_html}
  {why_html}
  {tactic_html}
  {sa_html}
  {ci_html}
  <div class="mini-summary">
    <div class="mini-status">{status_chips or '<span class="muted small">no IOs</span>'}</div>
    {next_target_html}
  </div>
  <div class="muted small mini-verdict-reason">{escape(verdict_reason)}</div>
</div>
"""


def render_decisions_panel(decisions: List[Decision], limit: int = 12) -> str:
    if not decisions:
        body = ('<div class="muted small">No decisions logged yet in '
                '<code>decisions/log.md</code>.</div>')
        return f'<div class="panel"><div class="panel-title">Recent Decisions</div>{body}</div>'
    recent = sorted(decisions, key=lambda d: d.date, reverse=True)[:limit]
    rows = []
    for d in recent:
        align = "aligned" if d.is_constraint_aligned else "off"
        align_label = "on-constraint" if d.is_constraint_aligned else "off-constraint"
        rows.append(
            f'<div class="decision-row">'
            f'<div class="decision-date">{d.date.isoformat()}</div>'
            f'<div class="decision-body">'
            f'<div class="decision-text">{escape(d.decision)}</div>'
            f'<div class="decision-meta muted small">'
            f'<span class="decision-align decision-align-{align}">{align_label}</span> '
            f'{escape(d.constraint_addressed or "—")}</div>'
            f'</div></div>'
        )
    return (f'<div class="panel"><div class="panel-title">Recent Decisions '
            f'<span class="muted small">(latest {len(recent)} of {len(decisions)})</span></div>'
            f'<div class="decision-list">{"".join(rows)}</div></div>')


def render_drag_panel(drag: DragSignal, decisions: List[Decision]) -> str:
    total = len(decisions)
    aligned = sum(1 for d in decisions if d.is_constraint_aligned)
    if drag.self_reported:
        self_block = (f'<div class="drag-self"><div class="drag-self-label muted small">'
                      f'Self-reported (most recent weekly review)</div>'
                      f'<div class="drag-self-body">{escape(drag.self_reported)}</div></div>')
    else:
        self_block = ('<div class="drag-self"><div class="drag-self-label muted small">'
                      'Self-reported drag</div><div class="drag-self-body muted small">'
                      'No weekly review on file in <code>reviews/weekly/</code> yet.</div></div>')
    return f"""
<div class="panel">
  <div class="panel-title">Drag Indicator</div>
  <div class="drag-grid">
    <div class="drag-stat"><div class="drag-value">{drag.decisions_last_4w}</div>
      <div class="drag-label muted small">decisions logged in last 4 weeks</div></div>
    <div class="drag-stat"><div class="drag-value">{drag.off_constraint_count}</div>
      <div class="drag-label muted small">flagged off-constraint (4w)</div></div>
    <div class="drag-stat"><div class="drag-value">{aligned}/{total}</div>
      <div class="drag-label muted small">constraint-aligned all-time</div></div>
  </div>
  {self_block}
</div>
"""


def render_git_panel(g: GitStatus) -> str:
    if not g.available:
        return ('<div class="panel git-panel grey"><div class="panel-title">Memory / Git Status</div>'
                '<div class="muted small">Not a git repository — backup status unavailable.</div></div>')
    if g.error:
        return (f'<div class="panel git-panel grey"><div class="panel-title">Memory / Git Status</div>'
                f'<div class="muted small">git status error: {escape(g.error)}</div></div>')
    now = datetime.now()

    def fmt_ago(dt):
        if dt is None:
            return "never"
        delta = now - dt
        if delta.days == 0:
            hours = delta.seconds // 3600
            return f"{delta.seconds // 60}m ago" if hours == 0 else f"{hours}h ago"
        return f"{delta.days}d ago"

    push_days = (now - g.last_pushed_at).days if g.last_pushed_at else 999
    has_pending = g.uncommitted_files > 0 or g.unpushed_commits > 0
    if g.remote_url is None:
        color, color_label = ("yellow", "LOCAL-ONLY")
    elif push_days > 14:
        color, color_label = "red", "OVERDUE"
    elif push_days > 7 and has_pending:
        color, color_label = "red", "AT RISK"
    elif push_days > 7 or has_pending:
        color, color_label = "yellow", "PENDING" if has_pending else "STALE"
    else:
        color, color_label = "green", "SYNCED"

    repo_short = (g.remote_url or "").split("/")[-1].replace(".git", "") or "(no remote)"
    unpushed_str = f"{g.unpushed_commits} unpushed commit{'s' if g.unpushed_commits != 1 else ''}"
    uncommitted_str = f"{g.uncommitted_files} uncommitted file{'s' if g.uncommitted_files != 1 else ''}"

    return f"""
<div class="panel git-panel {color}">
  <div class="git-head">
    <div class="git-title-block">
      <div class="panel-title git-panel-title">Memory / Git Status</div>
      <div class="muted small">Repo: <code>{escape(repo_short)}</code> &middot; branch <code>{escape(g.branch or '?')}</code></div>
    </div>
    <div class="git-status-badge {color}">{color_label}</div>
  </div>
  <div class="git-grid">
    <div class="git-stat">
      <div class="ts-label muted small">Last push to remote</div>
      <div class="git-stat-value">{fmt_ago(g.last_pushed_at)}</div>
      <div class="muted small">{g.last_pushed_at.strftime('%Y-%m-%d %H:%M') if g.last_pushed_at else '—'}</div>
    </div>
    <div class="git-stat">
      <div class="ts-label muted small">Last commit (local HEAD)</div>
      <div class="git-stat-value">{fmt_ago(g.last_commit_at)}</div>
      <div class="muted small"><code>{escape(g.last_commit_sha or '?')}</code> &middot; {escape((g.last_commit_message or '')[:60])}</div>
    </div>
    <div class="git-stat">
      <div class="ts-label muted small">Pending</div>
      <div class="git-stat-value">{uncommitted_str}</div>
      <div class="muted small">{unpushed_str}</div>
    </div>
  </div>
</div>
"""


def render_warnings_panel(warnings: List[str]) -> str:
    if not warnings:
        return ""
    items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
    return f"""
<div class="panel warn-panel">
  <div class="panel-title">Render Warnings <span class="muted small">({len(warnings)} file{'s' if len(warnings) != 1 else ''} skipped)</span></div>
  <div class="muted small" style="margin-bottom:0.6rem">
    These files could not be parsed and were skipped so the rest of the dashboard
    could render. Fix the file and regenerate.
  </div>
  <ul class="warn-list">{items}</ul>
</div>
"""


def render_archived_panel(archived: List[ArchivedProject]) -> str:
    if not archived:
        return ('<div class="panel" id="archived"><div class="panel-title">Archived Projects (0)</div>'
                '<div class="muted small">No archived projects yet.</div></div>')
    rows = []
    for ap in archived:
        date_str = ap.archived_date.isoformat() if ap.archived_date else "—"
        summary = " ".join(line.strip() for line in ap.summary.splitlines() if line.strip())
        summary_html = (f'<div class="archived-summary">{escape(summary)}</div>' if summary
                        else '<div class="muted small archived-summary">No archived summary recorded.</div>')
        rows.append(f'<div class="archived-row"><div class="archived-date">{escape(date_str)}</div>'
                    f'<div class="archived-body"><div class="archived-name">{escape(ap.display_name)}</div>'
                    f'{summary_html}</div></div>')
    return (f'<div class="panel" id="archived"><div class="panel-title">Archived Projects ({len(archived)})</div>'
            f'<div class="archived-list">{"".join(rows)}</div></div>')


def render_sidebar(state: BosState) -> str:
    links = [
        '<a class="nav-item" href="#bottleneck">Your Bottleneck</a>',
        '<a class="nav-item" href="#priorities">Priorities</a>',
        '<a class="nav-item" href="#details">Details</a>',
    ]
    links.append('<div class="nav-subnav">')
    for proj in state.projects:
        num = _project_number(proj.meta)
        links.append(f'<a class="nav-subitem" href="#proj-{escape(proj.meta.slug)}">'
                     f'<span class="nav-pnum">{escape(num)}</span> {escape(proj.meta.display_name)}</a>')
    links.append(f'<a class="nav-subitem nav-subitem-archived" href="#archived">Archived ({len(state.archived)})</a>')
    links.append('</div>')
    return f"""
<aside class="sidebar">
  <div class="sidebar-brand">
    <div class="brand-mark">BOS</div>
    <div class="brand-label">Bottleneck Dashboard</div>
  </div>
  <nav class="nav">{"".join(links)}</nav>
</aside>
"""


def render_dashboard(state: BosState, generated_at: datetime) -> str:
    all_ios = [io for proj in state.projects for io in flatten_ios(proj.tree)]
    io_statuses = [compute_io_status(io) for io in all_ios]
    verdict_color, verdict_reason = compute_verdict(io_statuses)
    drag = compute_drag(state.decisions, self_reported=getattr(state, "_drag_self", None))
    priorities = select_priority_ios(state.projects)

    # --- Top of the view: the only two things a new user needs ---
    top = (
        render_warnings_panel(state.warnings)
        + f'<section id="bottleneck">{render_bottleneck_header(state.constraint, verdict_color, verdict_reason, state.cloud_date)}</section>'
        + f'<section id="priorities">{render_priority_panel(priorities)}</section>'
    )

    # --- Progressive disclosure: everything else, collapsed by default ---
    five_steps = render_five_steps(state.constraint, state.cloud_date, io_statuses, state.projects, drag)

    project_sections = []
    for proj in state.projects:
        flat = flatten_ios(proj.tree)
        statuses = [compute_io_status(io) for io in flat]
        num = _project_number(proj.meta)
        v_color, _ = compute_verdict(statuses)
        project_sections.append(
            f'<details class="disclose" id="proj-{escape(proj.meta.slug)}">'
            f'<summary><span class="pip {v_color}"></span>'
            f'<span class="disclose-pnum">{escape(num)}</span> {escape(proj.meta.display_name)}</summary>'
            f'<div class="disclose-body">'
            + render_project_mini_dashboard(proj.meta, statuses, num)
            + render_io_tree(proj.tree, num)
            + '</div></details>'
        )

    history = (
        render_decisions_panel(state.decisions)
        + render_cadence_panel(state.constraint)
        + render_drag_panel(drag, state.decisions)
    )

    details = f"""
<div class="section-divider" id="details">The Full Picture <span class="muted small">(for when you want to dig in)</span></div>
<details class="disclose">
  <summary><span class="disclose-icon">▸</span> The Five Focusing Steps &mdash; where attention goes against your bottleneck</summary>
  <div class="disclose-body">{five_steps}</div>
</details>
<details class="disclose">
  <summary><span class="disclose-icon">▸</span> Projects &mdash; the full S&amp;T trees <span class="muted small">({len(state.projects)})</span></summary>
  <div class="disclose-body">{"".join(project_sections)}</div>
</details>
<details class="disclose">
  <summary><span class="disclose-icon">▸</span> History &amp; cadence &mdash; decisions, re-evaluation, drag</summary>
  <div class="disclose-body">{history}</div>
</details>
<details class="disclose">
  <summary><span class="disclose-icon">▸</span> Archived projects <span class="muted small">({len(state.archived)})</span></summary>
  <div class="disclose-body">{render_archived_panel(state.archived)}</div>
</details>
"""

    content = top + details
    gen_str = generated_at.strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>BOS Constraint Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>{CSS}</style>
</head>
<body>
<div class="app">
  {render_sidebar(state)}
  <main class="main">
    <div class="container">
      <div class="snapshot-banner muted small">
        Point-in-time snapshot generated {gen_str} from
        <code>{escape(str(state.root))}</code>. Regenerate with <code>/dashboard</code>.
      </div>
      {content}
      <p class="muted footer">
        Structural / Five-Focusing-Steps view &mdash; auto-derived from BOS markdown, no credentials.
        Live-metrics panels are a separate power-user add-on and are not included here.
      </p>
    </div>
  </main>
</div>
<script>{JS}</script>
</body>
</html>"""


# =====================================================================
# MAIN  (IO3 entry)
# =====================================================================

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a static BOS dashboard.html")
    parser.add_argument("--root", help="BOS root directory (default: auto-detect from cwd)")
    parser.add_argument("--out", help="output HTML path (default: <root>/dashboard.html)")
    parser.add_argument("--print", dest="do_print", action="store_true",
                        help="echo the output path after writing")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else find_bos_root()
    if not (root / "projects").is_dir():
        sys.stderr.write(
            f"ERROR: '{root}' does not look like a BOS root (no projects/ dir).\n"
            "Run from inside your BOS, or pass --root /path/to/bos.\n"
        )
        return 2

    state = read_bos(root)
    generated_at = datetime.now()
    html_doc = render_dashboard(state, generated_at)

    out_path = Path(args.out).resolve() if args.out else (root / "dashboard.html")
    out_path.write_text(html_doc, encoding="utf-8")

    # Always report a short summary to stderr so the skill can relay it.
    sys.stderr.write(
        f"Wrote {out_path} — {len(state.projects)} project(s), "
        f"{len(state.decisions)} decision(s), {len(state.warnings)} warning(s).\n"
    )
    if state.warnings:
        for w in state.warnings:
            sys.stderr.write(f"  warning: {w}\n")
    if args.do_print:
        print(str(out_path))
    return 0


# =====================================================================
# CSS + JS (inlined into the output; no external dependencies / no CDN)
# Fonts use system fallbacks so the file renders fully offline.
# =====================================================================

CSS = r"""
* { box-sizing: border-box; }
:root {
  --brand-blue:#00458c; --brand-blue-light:#4d8cc2; --brand-blue-dark:#003872;
  --brand-gold:#c7990b; --brand-gold-soft:#e6c76e; --brand-orange:#ff6b35; --brand-teal:#1eb2a6;
  --bg-page:#f5f5f5; --bg-panel:#ffffff; --bg-inset:#fafbff;
  --text-body:#00458c; --text-muted:#6b7d8f; --border:#c7990b; --border-soft:#e6c76e;
  --status-green:#1eb2a6; --status-yellow:#f59e0b; --status-red:#d62828; --status-grey:#9aa5b1;
  --anton: 'Anton', 'Arial Narrow', sans-serif;
  --serif: 'Merriweather', Georgia, 'Times New Roman', serif;
  --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, monospace;
}
body { font-family: var(--serif); margin:0; padding:0; background:var(--bg-page);
  color:var(--text-body); line-height:1.55; -webkit-font-smoothing:antialiased; }
.app { display:grid; grid-template-columns:240px 1fr; min-height:100vh; }
.sidebar { background:#fff; border-right:2px solid var(--border); padding:1.25rem 0;
  position:sticky; top:0; align-self:start; height:100vh; overflow-y:auto; }
.sidebar-brand { padding:0 1.25rem 1.25rem; border-bottom:2px solid var(--border-soft); margin-bottom:1rem; }
.brand-mark { font-family:var(--anton); font-size:1.6rem; color:var(--brand-blue); letter-spacing:0.06em; }
.brand-label { color:var(--text-muted); font-size:0.78rem; text-transform:uppercase; letter-spacing:0.08em; margin-top:0.15rem; }
.nav { display:flex; flex-direction:column; }
.nav-item { display:block; padding:0.65rem 1.25rem; color:var(--brand-blue); font-weight:bold;
  border-left:4px solid transparent; text-transform:uppercase; letter-spacing:0.05em; font-size:0.9rem; text-decoration:none; }
.nav-item:hover { background:#fafbff; }
.nav-subnav { display:flex; flex-direction:column; padding:0.25rem 0 0.5rem; background:#fafbff; border-left:4px solid transparent; }
.nav-subitem { display:block; padding:0.4rem 1.25rem 0.4rem 1.5rem; color:var(--brand-blue-light); font-size:0.82rem; text-decoration:none; }
.nav-subitem:hover { color:var(--brand-blue); }
.nav-pnum { font-family:var(--mono); font-size:0.72rem; color:var(--text-muted); margin-right:0.25rem; }
.nav-subitem-archived { margin-top:0.35rem; padding-top:0.55rem; border-top:1px dashed var(--border-soft);
  color:var(--text-muted); text-transform:uppercase; letter-spacing:0.06em; font-size:0.75rem; }
.main { min-width:0; }
.container { max-width:980px; margin:0 auto; padding:1.5rem; }
.snapshot-banner { margin-bottom:1rem; padding:0.5rem 0.75rem; background:var(--bg-inset);
  border:1px solid var(--border-soft); border-radius:5px; }
.section-divider { font-family:var(--anton); font-size:1.3rem; color:var(--brand-blue);
  text-transform:uppercase; letter-spacing:0.06em; margin:2rem 0 1rem; padding-bottom:0.5rem;
  border-bottom:2px solid var(--border); }
.muted { color:var(--text-muted); } .small { font-size:0.85rem; }
a { color:var(--brand-orange); text-decoration:none; } a:hover { text-decoration:underline; }
code { font-family:var(--mono); background:#fff7e0; padding:0 0.3em; border-radius:3px; color:var(--brand-blue-dark); font-size:0.92em; }
.footer { margin-top:2rem; color:var(--text-muted); }
.headline-status, .panel-title, .step-num, .constraint-statement, .drag-value { font-family:var(--anton); letter-spacing:0.04em; }

.headline { display:flex; align-items:center; padding:1.25rem 1.5rem; border-radius:8px;
  background:var(--bg-panel); border:2px solid var(--border); margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,69,140,0.06); }
.headline.green { border-left:8px solid var(--status-green); } .headline.yellow { border-left:8px solid var(--status-yellow); }
.headline.red { border-left:8px solid var(--status-red); } .headline.grey { border-left:8px solid var(--status-grey); }
.headline .dot { width:18px; height:18px; border-radius:50%; margin-right:1rem; flex-shrink:0; }
.headline.green .dot { background:var(--status-green); } .headline.yellow .dot { background:var(--status-yellow); }
.headline.red .dot { background:var(--status-red); } .headline.grey .dot { background:var(--status-grey); }
.headline-body { flex:1; }
.headline-label { font-size:0.85rem; color:var(--brand-blue-light); text-transform:uppercase; letter-spacing:0.1em; font-weight:bold; }
.headline-status { font-size:1.8rem; margin:0.1rem 0; color:var(--brand-blue); text-transform:uppercase; }
.headline-reason { color:var(--text-body); margin-bottom:0.3rem; }

.panel { background:var(--bg-panel); border:2px solid var(--border); border-radius:8px;
  padding:1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,69,140,0.06); }
.panel-title { font-size:1.1rem; color:var(--brand-blue); text-transform:uppercase; letter-spacing:0.1em;
  margin-bottom:1rem; border-bottom:2px solid var(--border-soft); padding-bottom:0.6rem; }
.warn-panel { border-color:var(--status-yellow); border-left:8px solid var(--status-yellow); background:#fffbf0; }
.warn-list { margin:0; padding-left:1.2rem; color:#7a5d05; font-size:0.88rem; line-height:1.6; }
.warn-list li { margin:0.2rem 0; font-family:var(--mono); }

.step { margin-bottom:1.3rem; padding:0.75rem 1rem 0.85rem; border-radius:6px; background:var(--bg-inset); border-left:4px solid var(--status-grey); }
.step:last-child { margin-bottom:0; }
.step-green { border-left-color:var(--status-green); } .step-yellow { border-left-color:var(--status-yellow); }
.step-red { border-left-color:var(--status-red); } .step-grey { border-left-color:var(--status-grey); }
.step-head { font-weight:bold; color:var(--brand-blue); margin-bottom:0.5rem; letter-spacing:0.05em; font-size:0.95rem; }
.step-num { display:inline-block; width:1.7rem; height:1.7rem; line-height:1.7rem; text-align:center;
  background:var(--brand-blue); color:#fff; border-radius:50%; font-size:0.95rem; margin-right:0.5rem; }
.step-count { margin-left:0.4rem; font-weight:normal; }
.step-body { padding-left:2.2rem; }
.constraint-statement { font-size:1.5rem; color:var(--brand-orange); margin-bottom:0.3rem; text-transform:uppercase; }
.step-analysis { margin-top:0.5rem; padding:0.6rem 0.85rem; background:var(--bg-panel); border-left:3px solid var(--brand-blue-light);
  border-radius:0 4px 4px 0; line-height:1.55; color:var(--brand-blue-dark); font-size:0.95rem; }
.step-analysis em { color:var(--brand-blue); font-style:normal; font-weight:bold; }
.step-analysis-green { border-left-color:var(--status-green); } .step-analysis-yellow { border-left-color:var(--status-yellow); }
.step-analysis-red { border-left-color:var(--status-red); } .step-analysis-grey { border-left-color:var(--status-grey); color:var(--text-muted); }
.step-others { margin-top:0.5rem; padding-left:0.85rem; border-left:2px dotted var(--border-soft); }

.copy-id { cursor:pointer; user-select:none; display:inline-block; padding:0.15rem 0.5rem; border-radius:3px;
  border:1px dashed transparent; transition:background 0.15s, border-color 0.15s; }
.copy-id:hover { background:#fff7e0; border-color:var(--border-soft); }
.copy-id.copied { background:#d4f1ec; border-color:#9ed8cc; color:#0f6f64; }
.copy-id.copy-failed { background:#fde4e4; border-color:#f4b4b4; color:#a01818; }

.pip { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:0.5rem; vertical-align:middle; border:1px solid rgba(0,0,0,0.08); }
.pip.green { background:var(--status-green); } .pip.yellow { background:var(--status-yellow); }
.pip.red { background:var(--status-red); } .pip.grey { background:var(--status-grey); }

.cadence-row { display:flex; justify-content:space-between; padding:0.35rem 0; border-bottom:1px dashed var(--border-soft); }
.cadence-row:last-child { border-bottom:none; }
.cadence-artifact { color:var(--brand-blue); flex:1; }
.cadence-when { color:var(--text-muted); font-size:0.85rem; min-width:90px; text-align:right; }
.overdue { color:var(--brand-orange); font-weight:bold; }

.io-section { margin-bottom:1.5rem; } .io-section:last-child { margin-bottom:0; }
.io-section-title { font-family:var(--anton); font-size:0.95rem; color:var(--brand-blue); text-transform:uppercase;
  letter-spacing:0.06em; margin-bottom:0.75rem; padding-bottom:0.35rem; border-bottom:1px dashed var(--border-soft); }
.io-section-closed .io-card { opacity:0.75; } .io-section-closed .io-section-title { color:var(--text-muted); }
.io-empty { padding:0.75rem 0; font-style:italic; }
.io-list { display:flex; flex-direction:column; gap:0.85rem; }
.io-card { background:var(--bg-panel); border:1px solid var(--border-soft); border-left:5px solid var(--status-grey);
  border-radius:6px; padding:1rem 1.1rem; box-shadow:0 1px 2px rgba(0,69,140,0.04); display:flex; flex-direction:column; gap:0.5rem; }
.io-card-green { border-left-color:var(--status-green); } .io-card-yellow { border-left-color:var(--status-yellow); }
.io-card-red { border-left-color:var(--status-red); } .io-card-grey { border-left-color:var(--status-grey); }
.io-card-head { display:flex; align-items:center; gap:0.55rem; }
.pip-lg { width:12px; height:12px; flex-shrink:0; }
.io-number { font-family:var(--anton); font-size:0.95rem; color:var(--text-muted); letter-spacing:0.05em; white-space:nowrap; }
.io-card-name { color:var(--brand-blue); font-weight:bold; font-size:1.05rem; line-height:1.3; flex:1; }
.crit-tag { display:inline-block; font-family:var(--anton); font-size:0.72rem; padding:0.2rem 0.65rem; border-radius:3px;
  text-transform:uppercase; letter-spacing:0.07em; border:1px solid transparent; margin-left:auto; flex-shrink:0; align-self:flex-start; }
.crit-tag.tag-critical { background:#fde4e4; color:#a01818; border-color:#f4b4b4; }
.crit-tag.tag-non-critical { background:#ececec; color:#4a4a4a; border-color:#c4c4c4; }
.status-chip { display:inline-block; font-size:0.7rem; padding:0.18rem 0.55rem; border-radius:10px; text-transform:uppercase;
  letter-spacing:0.05em; font-weight:bold; border:1px solid var(--border-soft); background:var(--bg-inset); color:var(--brand-blue-dark); }
.status-chip.status-in-progress { background:#fff3d6; color:#8b6914; border-color:#e6c76e; }
.status-chip.status-open { background:#e8f0fb; color:var(--brand-blue); border-color:#aac8e6; }
.status-chip.status-blocked { background:#fde4e4; color:#a01818; border-color:#f4b4b4; }
.status-chip.status-done { background:#d4f1ec; color:#0f6f64; border-color:#9ed8cc; }
.status-chip.status-deferred { background:#ececec; color:#4a4a4a; border-color:#c4c4c4; }
.status-chip.status-needs-update { background:#f4ddf4; color:#6a2a6a; border-color:#d4a8d4; }
.io-target { font-family:var(--mono); font-size:0.85rem; color:var(--brand-blue-dark); display:flex; align-items:center; gap:0.25rem; flex-wrap:wrap; }
.io-target-label { text-transform:uppercase; font-family:var(--anton); color:var(--text-muted); letter-spacing:0.05em; font-size:0.72rem; margin-right:0.25rem; }
.io-target-date { font-weight:bold; }
.countdown { font-family:var(--mono); font-size:0.78rem; padding:0.1rem 0.45rem; border-radius:3px; background:var(--bg-inset);
  color:var(--text-muted); border:1px solid var(--border-soft); margin-left:0.3rem; }
.countdown.due { background:#fff3d6; color:#8b6914; border-color:#e6c76e; }
.countdown.overdue { background:#fde4e4; color:#a01818; border-color:#f4b4b4; }
.io-field { display:block; width:100%; padding-top:0.35rem; border-top:1px dashed var(--border-soft); }
.io-field:first-of-type { border-top:none; padding-top:0; }
.io-field-label { font-family:var(--anton); font-size:0.7rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.2rem; }
.io-field-content { font-size:0.92rem; line-height:1.55; color:var(--text-body); word-wrap:break-word; overflow-wrap:break-word; }
.io-field-leaf .io-field-content { color:var(--text-muted); }
.io-children { margin-top:0.85rem; margin-left:1.5rem; padding-left:1rem; border-left:2px solid var(--border-soft); display:flex; flex-direction:column; gap:0.85rem; }
.io-children .io-card { background:var(--bg-inset); }
.io-children .io-children .io-card { background:var(--bg-panel); }
.io-deps { padding-top:0.45rem; border-top:1px dashed var(--border-soft); font-family:var(--mono); font-size:0.82rem; }
.io-deps-label { font-family:var(--anton); text-transform:uppercase; letter-spacing:0.05em; font-size:0.72rem; color:var(--text-muted); margin-right:0.25rem; }

.project-mini { padding:1.5rem 1.5rem 1.25rem; }
.project-mini-head { display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;
  padding-bottom:0.6rem; border-bottom:2px solid var(--border-soft); gap:1rem; }
.project-mini-titlebox { display:flex; flex-direction:column; gap:0.2rem; }
.project-mini-pnum { font-family:var(--anton); font-size:0.85rem; color:var(--text-muted); letter-spacing:0.08em; text-transform:uppercase; }
.project-mini-pnum .copy-id { color:var(--brand-blue); padding:0.05rem 0.4rem; }
.project-mini-title { font-family:var(--anton); font-size:1.7rem; color:var(--brand-blue); text-transform:uppercase; letter-spacing:0.04em; line-height:1.1; }
.verdict-badge { font-family:var(--anton); font-size:0.95rem; padding:0.3rem 0.8rem; border-radius:4px; letter-spacing:0.08em; color:#fff; flex-shrink:0; }
.verdict-badge.verdict-green { background:var(--status-green); } .verdict-badge.verdict-yellow { background:var(--status-yellow); color:#4a3a04; }
.verdict-badge.verdict-red { background:var(--status-red); } .verdict-badge.verdict-grey { background:var(--status-grey); }
.l1-section-label { font-family:var(--anton); font-size:0.75rem; color:var(--text-muted); letter-spacing:0.1em; text-transform:uppercase; margin-bottom:0.5rem; }
.l1-field { margin-bottom:0.85rem; padding:0.7rem 0.9rem; background:var(--bg-inset); border-left:3px solid var(--brand-orange); border-radius:0 4px 4px 0; }
.l1-field-missing { border-left-color:var(--status-yellow); background:#fff7e0; }
.l1-field-label { font-family:var(--anton); font-size:0.78rem; color:var(--brand-blue); text-transform:uppercase; letter-spacing:0.08em; margin-bottom:0.3rem; }
.l1-field-missing .l1-field-label { color:#7a5d05; }
.l1-field-content { font-size:0.98rem; line-height:1.5; color:var(--brand-blue-dark); }
.l1-field-missing .l1-field-content { color:#7a5d05; font-style:italic; font-size:0.9rem; }
.mini-ci { margin:1rem 0 0.85rem; padding:0.55rem 0.9rem; background:var(--bg-inset); border-radius:4px; display:flex; align-items:center; gap:0.5rem; flex-wrap:wrap; }
.mini-ci-label { font-family:var(--anton); font-size:0.72rem; color:var(--text-muted); text-transform:uppercase; letter-spacing:0.07em; margin-right:0.4rem; }
.step-badge { font-family:var(--anton); font-size:0.78rem; padding:0.2rem 0.7rem; border-radius:3px; text-transform:uppercase; letter-spacing:0.06em; color:#fff; }
.step-badge.step-exploit { background:var(--brand-blue-light); } .step-badge.step-subordinate { background:var(--brand-gold); }
.step-badge.step-elevate { background:var(--brand-orange); }
.mini-summary { display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; flex-wrap:wrap; padding-top:0.5rem; border-top:1px dashed var(--border-soft); }
.mini-status { display:flex; flex-wrap:wrap; gap:0.4rem; }
.mini-target { text-align:right; font-family:var(--mono); font-size:0.9rem; color:var(--brand-blue-dark); }
.mini-target-date { font-weight:bold; } .mini-target-io { color:var(--text-muted); }
.mini-verdict-reason { margin-top:0.5rem; font-style:italic; }

.decision-list { display:flex; flex-direction:column; }
.decision-row { display:grid; grid-template-columns:100px 1fr; gap:0.85rem; padding:0.6rem 0; border-bottom:1px dashed var(--border-soft); }
.decision-row:last-child { border-bottom:none; }
.decision-date { font-family:var(--mono); font-size:0.82rem; color:var(--brand-blue); font-weight:bold; font-variant-numeric:tabular-nums; }
.decision-text { color:var(--brand-blue-dark); font-size:0.92rem; line-height:1.5; }
.decision-meta { margin-top:0.2rem; }
.decision-align { font-family:var(--anton); font-size:0.68rem; padding:0.1rem 0.45rem; border-radius:3px; text-transform:uppercase; letter-spacing:0.05em; }
.decision-align-aligned { background:#d4f1ec; color:#0f6f64; } .decision-align-off { background:#fde4e4; color:#a01818; }

.drag-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:0.75rem; }
.drag-stat { background:var(--bg-inset); border:1px solid var(--border); border-radius:6px; padding:1rem 0.85rem; text-align:center; }
.drag-value { font-size:2.2rem; color:var(--brand-orange); line-height:1.1; }
.drag-label { margin-top:0.3rem; }
.drag-self { margin-top:0.85rem; padding:1rem; background:var(--bg-inset); border:1px solid var(--border); border-radius:6px; }
.drag-self-label { margin-bottom:0.4rem; text-transform:uppercase; letter-spacing:0.05em; font-weight:bold; }
.drag-self-body { color:var(--brand-blue-dark); white-space:pre-wrap; }

.git-panel.green { border-left:8px solid var(--status-green); } .git-panel.yellow { border-left:8px solid var(--status-yellow); }
.git-panel.red { border-left:8px solid var(--status-red); } .git-panel.grey { border-left:8px solid var(--status-grey); }
.git-head { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1rem; }
.git-panel-title { margin-bottom:0.2rem; border-bottom:none; padding-bottom:0; }
.git-status-badge { font-family:var(--anton); font-size:1rem; padding:0.3rem 0.8rem; border-radius:4px; letter-spacing:0.08em; color:#fff; }
.git-status-badge.green { background:var(--status-green); } .git-status-badge.yellow { background:var(--status-yellow); color:#4a3a04; }
.git-status-badge.red { background:var(--status-red); } .git-status-badge.grey { background:var(--status-grey); }
.git-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:1rem; margin-bottom:0.5rem; }
.git-stat { background:var(--bg-inset); border:1px solid var(--border); border-radius:6px; padding:0.85rem; }
.git-stat-value { font-family:var(--anton); color:var(--brand-blue); font-size:1.3rem; margin:0.2rem 0; }
.ts-label { text-transform:uppercase; letter-spacing:0.05em; }

.archived-list { display:flex; flex-direction:column; gap:1rem; }
.archived-row { display:grid; grid-template-columns:120px 1fr; gap:1rem; padding:0.85rem; background:var(--bg-inset); border:1px solid var(--border); border-radius:6px; }
.archived-date { font-family:var(--mono); color:var(--brand-blue); font-weight:bold; font-variant-numeric:tabular-nums; font-size:0.95rem; }
.archived-name { font-family:var(--anton); color:var(--brand-blue); font-size:1.05rem; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:0.35rem; }
.archived-summary { line-height:1.55; color:var(--brand-blue-dark); font-size:0.92rem; }

/* Bottleneck header (top of the shipped view) */
.bottleneck { background:var(--bg-panel); border:2px solid var(--border); border-radius:8px;
  padding:1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,69,140,0.06); }
.bottleneck.green { border-left:8px solid var(--status-green); } .bottleneck.yellow { border-left:8px solid var(--status-yellow); }
.bottleneck.red { border-left:8px solid var(--status-red); } .bottleneck.grey { border-left:8px solid var(--status-grey); }
.bn-top { display:flex; justify-content:space-between; align-items:center; gap:1rem; margin-bottom:0.6rem; }
.bn-label { font-family:var(--anton); font-size:0.85rem; color:var(--brand-blue-light); text-transform:uppercase; letter-spacing:0.12em; }
.bn-badge { font-family:var(--anton); font-size:0.9rem; padding:0.3rem 0.85rem; border-radius:4px; letter-spacing:0.06em; color:#fff; white-space:nowrap; }
.bn-badge-green { background:var(--status-green); } .bn-badge-yellow { background:var(--status-yellow); color:#4a3a04; }
.bn-badge-red { background:var(--status-red); } .bn-badge-grey { background:var(--status-grey); }
.bn-statement { font-family:var(--anton); font-size:1.7rem; line-height:1.15; color:var(--brand-orange); text-transform:uppercase; letter-spacing:0.02em; margin-bottom:0.5rem; }
.bn-statement-missing { color:#7a5d05; font-style:italic; font-size:1.05rem; text-transform:none; }
.bn-reason { margin-bottom:0.2rem; } .bn-freshness { margin-top:0.1rem; }

/* Priority panel — the 3-4 big-ticket items */
.prio-panel { border-left:8px solid var(--brand-orange); }
.prio-list { display:flex; flex-direction:column; gap:0.85rem; }
.prio-empty { padding:0.5rem 0; font-style:italic; }
.prio-card { background:var(--bg-inset); border:1px solid var(--border-soft); border-left:5px solid var(--status-grey);
  border-radius:6px; padding:0.9rem 1.1rem; display:flex; flex-direction:column; gap:0.4rem; }
.prio-green { border-left-color:var(--status-green); } .prio-yellow { border-left-color:var(--status-yellow); }
.prio-red { border-left-color:var(--status-red); } .prio-grey { border-left-color:var(--status-grey); }
.prio-head { display:flex; align-items:center; gap:0.55rem; flex-wrap:wrap; }
.prio-chip { font-family:var(--anton); font-size:0.72rem; padding:0.2rem 0.7rem; border-radius:3px; text-transform:uppercase;
  letter-spacing:0.07em; color:#fff; flex-shrink:0; }
.prio-chip.chip-resolve { background:var(--brand-blue-light); }
.prio-chip.chip-elevate { background:var(--brand-orange); }
.prio-chip.chip-unscoped { background:var(--status-grey); }
.prio-name { color:var(--brand-blue); font-weight:bold; font-size:1.08rem; line-height:1.3; flex:1; min-width:60%; }
.prio-meta { display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; }
.prio-project { font-family:var(--anton); font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em; }
.prio-target { font-family:var(--mono); font-size:0.85rem; color:var(--brand-blue-dark); }
.prio-why { font-style:italic; }

/* Progressive-disclosure sections */
.disclose { border:2px solid var(--border-soft); border-radius:8px; background:var(--bg-panel); margin-bottom:1rem; overflow:hidden; }
.disclose > summary { cursor:pointer; padding:1rem 1.25rem; font-family:var(--anton); font-size:1rem; color:var(--brand-blue);
  text-transform:uppercase; letter-spacing:0.05em; list-style:none; display:flex; align-items:center; gap:0.5rem; }
.disclose > summary::-webkit-details-marker { display:none; }
.disclose > summary:hover { background:#fafbff; }
.disclose-icon { display:inline-block; transition:transform 0.15s; color:var(--brand-orange); }
.disclose[open] > summary .disclose-icon { transform:rotate(90deg); }
.disclose-pnum { font-family:var(--mono); font-size:0.78rem; color:var(--text-muted); }
.disclose-body { padding:0 1.25rem 1.25rem; }
/* Per-project nested disclosure inside the Projects group */
.disclose .disclose { border-color:var(--border-soft); margin-bottom:0.75rem; }
.disclose .disclose-body .panel { box-shadow:none; }

html { scroll-behavior:smooth; }
section { scroll-margin-top:1rem; }
.disclose { scroll-margin-top:1rem; }

@media (max-width:800px) { .app { grid-template-columns:1fr; } .sidebar { position:relative; height:auto; border-right:none; border-bottom:2px solid var(--border); } }
@media (max-width:700px) { .git-grid, .drag-grid, .archived-row, .decision-row { grid-template-columns:1fr; }
  .project-mini-head, .mini-summary { flex-direction:column; align-items:flex-start; } .mini-target { text-align:left; } }
"""

JS = r"""
// Open a target <details> (and all its ancestor <details>) when navigated to via
// an in-page anchor, so priority/sidebar links never scroll to hidden content.
function openToHash() {
  var id = (location.hash || '').replace('#', '');
  if (!id) return;
  var el = document.getElementById(id);
  if (!el) return;
  var node = el;
  while (node) {
    if (node.tagName === 'DETAILS') node.open = true;
    node = node.parentElement;
  }
  // If the element itself is a <details>, open it too.
  if (el.tagName === 'DETAILS') el.open = true;
  setTimeout(function () { el.scrollIntoView({behavior: 'smooth', block: 'start'}); }, 0);
}
window.addEventListener('hashchange', openToHash);
window.addEventListener('DOMContentLoaded', openToHash);

document.addEventListener('click', function (e) {
  var link = e.target.closest('a[href^="#"]');
  if (link) {
    var id = link.getAttribute('href').slice(1);
    var el = id && document.getElementById(id);
    if (el) {
      var node = el;
      while (node) { if (node.tagName === 'DETAILS') node.open = true; node = node.parentElement; }
      if (el.tagName === 'DETAILS') el.open = true;
    }
  }
  var target = e.target.closest('.copy-id');
  if (!target) return;
  var text = target.dataset.copy || target.textContent.trim();
  var restore = target.innerHTML;
  var finish = function (ok) {
    target.classList.add(ok ? 'copied' : 'copy-failed');
    target.textContent = ok ? 'Copied' : 'Copy failed';
    setTimeout(function () { target.classList.remove('copied', 'copy-failed'); target.innerHTML = restore; }, 1200);
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(function () { finish(true); }, function () { finish(false); });
  } else {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); finish(true); } catch (err) { finish(false); }
    document.body.removeChild(ta);
  }
});
"""


if __name__ == "__main__":
    raise SystemExit(main())
