"""Project activity uses a narrow projection of recorded workflow executions."""

import json
from pathlib import Path
import sqlite3

from .agent_runs import run_is_active
from .decisions import SCOPE

RECENT_LIMIT = 8
INTAKE_TASKS = {
    "coach-field": "Ask your AI partner about an intake response",
    "review-value": "Review the value proposition",
    "compose-value": "Draft the value proposition",
    "seed-value": "Draft intake answers from selected material",
    "context-questions": "Suggest context questions",
    "assess-change": "Assess new material against the intake",
}
REQUIREMENT_TASKS = {
    "draft": "Draft a requirement and acceptance criteria",
    "review": "Review requirement wording and acceptance criteria",
    "tailor-scaffold": "Adapt the requirement scaffold to the intake",
    "review-scaffold": "Review the proposed scaffold",
    "prepare-goals": "Propose goals and success measures",
    "coach-item": "Ask your AI partner about a requirement, goal, or measure",
}
DOMAIN_TASKS = {
    "domain-conversation": "Review work against the selected project context",
    "domain-coaching": "Review a domain deliverable",
    "domain-packet-interpretation": "Assess a context packet using domain guidance",
    "domain-brief-objectives": "Suggest domain objectives",
    "domain-design-brief": "Draft a Working brief and objectives",
    "design-pdf-review": "Review prototype screens against requirements and Research",
}


def function_for(row):
    """Use registered workflow functions instead of a private prompt or a persona ID."""
    persona, skill = row["persona"], row["skill"]
    if persona == "P02" and skill in INTAKE_TASKS:
        return "Business Intent AI partner", "Business Intent", INTAKE_TASKS[skill]
    if persona == "P04" and skill in REQUIREMENT_TASKS:
        return "Requirements Assistant", "Requirements", REQUIREMENT_TASKS[skill]
    if persona not in {"P06", "P07", "P12"} or skill not in DOMAIN_TASKS:
        return None
    default_domain = {"P06": "research", "P12": "design"}.get(persona, "domain")
    domain = row["scope"].removeprefix("domain:") if row["scope"].startswith("domain:") else default_domain
    where = f"{domain.replace('-', ' ').capitalize()} workbench"
    if skill == "design-pdf-review" or row["agent"] == "design-visual-coach":
        return "Design Screen Reviewer", "Design workbench", DOMAIN_TASKS["design-pdf-review"]
    if skill == "domain-design-brief":
        return domain.replace("-", " ").title()+" Brief Drafter", where, DOMAIN_TASKS[skill]
    if skill == "domain-packet-interpretation":
        return "Context Packet Reviewer", where, DOMAIN_TASKS[skill]
    if skill == "domain-brief-objectives":
        return "Domain Objectives AI partner", where, DOMAIN_TASKS[skill]
    name = {"research": "Research Evidence AI partner", "design": "Design Work AI partner"}.get(domain, "Domain Work AI partner")
    return name, where, DOMAIN_TASKS[skill]


def linked_assignment(db, row):
    """Look up only the exact shared assignment supplied as a run input."""
    raw = row["assignment"]
    if not raw:
        return None
    try:
        ref = json.loads(raw)
    except (TypeError, ValueError):
        return None
    if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or type(ref.get("revision")) is not int:
        return None
    match = db.execute("""
        SELECT json_extract(body, '$.title') AS title FROM records
        WHERE id = ? AND revision = ? AND scope = ? AND kind = 'project-work-request'
    """, (ref["id"], ref["revision"], SCOPE)).fetchone()
    if match:
        return dict(ref=dict(id=ref["id"], revision=ref["revision"]), title=match["title"])
    return None


def agent_activity(path):
    """Read current and recent executions without acquiring the project write lock."""
    db = sqlite3.connect(Path(path).as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("""
            SELECT run.id, run.scope,
                   json_extract(run.body, '$.persona_id') AS persona,
                   json_extract(run.body, '$.agent') AS agent,
                   json_extract(run.body, '$.skill') AS skill,
                   json_extract(run.body, '$.mode') AS mode,
                   json_extract(run.body, '$.actor') AS requester,
                   json_extract(run.body, '$.started_at') AS started_at,
                   json_extract(run.body, '$.finished_at') AS finished_at,
                   json_extract(run.body, '$.status') AS status,
                   COALESCE(json_extract(run.body, '$.context.work_request.current'),
                            json_extract(run.body, '$.context.work_request.ref'),
                            json_extract(run.body, '$.context.work_request.selected'),
                            json_extract(run.body, '$.context.domain_brief.current.ref'),
                            json_extract(run.body, '$.basis')) AS assignment
            FROM records AS run
            JOIN (SELECT id, MAX(revision) AS revision FROM records
                  WHERE kind = 'agent-execution' GROUP BY id) AS latest
              ON run.id = latest.id AND run.revision = latest.revision
            WHERE json_extract(run.body, '$.purpose') = 'workflow'
              AND json_extract(run.body, '$.mode') IN ('live', 'simulated')
            ORDER BY julianday(COALESCE(finished_at, started_at)) DESC, run.rowid DESC
        """)
        active, recent = [], []
        for row in rows:
            function = function_for(row)
            if not function:
                continue
            status = row["status"]
            running = status == "running" and run_is_active(path, row["id"])
            if not running and len(recent) >= RECENT_LIMIT:
                continue
            if status == "running" and not running:
                status = "unknown"
            name, where, task = function
            item = dict(agent=name, where=where, task=task, requester=row["requester"],
                        mode=row["mode"], status=status, started_at=row["started_at"],
                        finished_at=row["finished_at"], assignment=linked_assignment(db, row))
            (active if running else recent).append(item)
        return dict(active=active, recent=recent)
    finally:
        db.close()
