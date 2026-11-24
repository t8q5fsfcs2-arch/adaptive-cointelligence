"""Project-wide reporting over shared records and their exact versions."""

from dataclasses import asdict
import json

from .core import Ref
from .decisions import SCOPE

PAGE_SIZE = 20

ISSUE_EVENTS = {
    "raised": "Issue raised",
    "investigate": "Investigation assigned",
    "assign": "Issue reassigned",
    "request-evidence": "Evidence requested",
    "answer-request": "Information received",
    "withdraw-request": "Information request withdrawn",
    "defer": "Issue deferred",
    "reopened": "Issue reopened",
    "basis-refreshed": "Issue context reviewed",
    "requirement-review-opened": "Requirement review opened",
    "review-linked": "Requirement review linked",
    "intent-response-requested": "Sponsor response requested",
    "resolved": "Issue resolved",
    "integrity-review-attached": "AI partner attached",
    "integrity-finding-disposed": "Integrity finding disposition recorded",
    "integrity-reconciliation-recorded": "Cross-domain reconciliation response recorded",
}

# Each kind uses its recorded event time. Ordinary edits and read receipts are excluded.
EVENTS = """
    SELECT rowid AS sequence, id, revision, kind, body,
        CASE kind
            WHEN 'project' THEN json_extract(body, '$.created_at')
            WHEN 'decision-case' THEN json_extract(body, '$.created_at')
            WHEN 'contribution' THEN json_extract(body, '$.published_at')
            WHEN 'project-design-brief' THEN json_extract(body, '$.published_at')
            WHEN 'project-work-request' THEN
                CASE WHEN revision = 1 THEN json_extract(body, '$.at')
                     ELSE json_extract(body, '$.updated_at') END
            ELSE json_extract(body, '$.at')
        END AS at
    FROM records
    WHERE scope = ? AND (
        (kind = 'project' AND revision = 1)
        OR kind IN ('intent-decision', 'decision', 'contribution',
                    'project-design-brief', 'project-work-request', 'demo-delivery-receipt',
                    'human-review', 'intake-assessment', 'decision-rights', 'decision-rights-review')
        OR (kind='decision-authority-event' AND json_extract(body,'$.action')!='review')
        OR (kind = 'decision-case' AND revision = 1 AND NOT EXISTS (
            SELECT 1 FROM records AS event
            WHERE event.scope = records.scope AND event.kind = 'bridge-issue-event'
              AND json_extract(event.body, '$.action') = 'requirement-review-opened'
              AND json_extract(event.body, '$.linked.id') = records.id
        ))
        OR (kind = 'bridge-issue-event' AND
            json_extract(body, '$.action') NOT IN ('comment', 'linked-review-updated'))
    )
"""


def timeline_page(store, before=None):
    """Read one page, ordered by event time with insertion order breaking ties."""
    if before is not None and (type(before) is not int or not 0 < before < 2**63):
        raise ValueError("Choose an earlier timeline page from this project.")
    rows = store.db.execute(
        f"""WITH events AS ({EVENTS})
        SELECT * FROM events AS event
        WHERE julianday(event.at) IS NOT NULL
          AND (? IS NULL OR (julianday(event.at), event.sequence) <
              (SELECT julianday(at), sequence FROM events WHERE sequence = ?))
        ORDER BY julianday(event.at) DESC, event.sequence DESC
        LIMIT ?""",
        (SCOPE, before, before, PAGE_SIZE + 1),
    ).fetchall()
    return {
        "entries": [timeline_entry(store, row) for row in rows[:PAGE_SIZE]],
        "before": rows[PAGE_SIZE - 1]["sequence"] if len(rows) > PAGE_SIZE else None,
    }


def shared_body(store, raw):
    if not raw:
        return {}
    try:
        return store.read(Ref(**raw), {SCOPE})["body"]
    except PermissionError:
        return {}


def timeline_entry(store, row):
    body = json.loads(row["body"])
    kind, revision = row["kind"], row["revision"]
    entry = {
        "ref": asdict(Ref(row["id"], revision)),
        "at": row["at"],
        "actor": body.get("actor"),
        "category": "",
        "subject": body.get("title", ""),
        "detail": "",
    }
    if kind == "project":
        entry.update(category="Project created", actor=body.get("created_by"))
    elif kind == "bridge-issue-event":
        issue_ref = body["issue"]
        issue = shared_body(store, issue_ref)
        entry.update(
            category=ISSUE_EVENTS.get(body["action"], "Issue updated"),
            subject=issue.get("title", ""),
            detail=body.get("note", ""),
            issue=issue_ref,
            linked=body.get("linked"),
        )
    elif kind == "project-work-request":
        category = {
            "accepted": "Working brief accepted",
            "cancelled": "Working brief cancelled",
        }.get(body["status"], "Working brief sent")
        entry.update(
            category=category,
            detail=body.get("cancellation_reason") or body.get("objective", ""),
            actor=body.get("requested_by") if revision == 1 else body.get("updated_by"),
            recipient=body.get("recipient"),
            work_request=row["id"],
        )
    elif kind == "contribution":
        domain = body.get("domain") or "Domain"
        action = "published work" if revision == 1 else "published revised work"
        entry.update(
            category=f"{domain} {action}",
            actor=body.get("owner"),
            detail=body.get("handoff", {}).get("downstream_needs") or body.get("observation", ""),
            packet=body.get("packet"),
        )
    elif kind == "project-design-brief":
        entry.update(
            category="Working brief updated" if body.get("previous") else "Working brief shared",
            detail=", ".join(body.get("changed_elements", [])),
            actor=body.get("completed_by") or body.get("owner"),
            design_brief=entry["ref"],
        )
    elif kind == "intent-decision":
        published = body.get("disposition") == "publish-for-investigation"
        entry.update(
            category="Business direction published" if published else "Business direction decision",
            subject="Business intent",
            detail=body.get("rationale", ""),
            linked=body.get("intent") or body.get("case"),
        )
    elif kind == "decision":
        case = shared_body(store, body.get("case"))
        target_ref = body.get("result_requirement") or case.get("target")
        requirement = shared_body(store, target_ref)
        category = {"approve": "Requirement approved", "reject": "Requirement change rejected",
                    "defer": "Requirement decision deferred"}.get(body.get("disposition"), "Requirement decision")
        entry.update(
            category=category,
            subject=requirement.get("title", ""),
            detail=body.get("rationale", ""),
            linked=target_ref,
            case=body.get("case"),
        )
    elif kind in {"human-review", "decision-case"}:
        case_ref = body.get("case") if kind == "human-review" else entry["ref"]
        case = shared_body(store, case_ref)
        requirement = shared_body(store, case.get("target"))
        entry.update(
            category="Requirement review submitted" if kind == "human-review" else "Requirement review opened",
            subject=requirement.get("title") or case.get("proposal", {}).get("text", "")[:110],
            detail=body.get("rationale", "") if kind == "human-review" else case.get("proposal", {}).get("text", ""),
            actor=body.get("actor") if kind == "human-review" else body.get("created_by"),
            case=case_ref,
            linked=case.get("target"),
        )
    elif kind == "intake-assessment":
        entry.update(category="Business direction review submitted", subject="Business Intent",
                     detail=body.get("rationale", ""))
        # Assessments predate a direct case reference; recover only an exact shared link.
        case = store.db.execute("""SELECT r.id,r.revision FROM records r,
            json_each(r.body, '$.reviews') AS review
            WHERE r.scope=? AND r.kind='intake-case'
              AND json_extract(review.value, '$.id')=?
              AND json_extract(review.value, '$.revision')=?
            ORDER BY r.rowid LIMIT 1""", (SCOPE, row["id"], revision)).fetchone()
        if case:
            entry["intake_case"] = asdict(Ref(case["id"], case["revision"]))
    elif kind == "decision-rights":
        entry.update(category="Decision rights updated",subject="Project decision rights",detail=body.get("reason",""),decision_rights=True)
    elif kind in {"decision-authority-event","decision-rights-review"}:
        target=body.get("target") or body.get("issue")
        target_kind=body.get("target_kind","bridge-issue")
        categories={"refresh":"Decision rights refreshed","delegate":"Decision delegation updated","escalate":"Decision escalated","respond":"Escalation response recorded","review":"Required assessment recorded"}
        entry.update(category=categories.get(body.get("action"),"Required assessment recorded"),detail=body.get("reason",body.get("rationale","")))
        if target:
            b=shared_body(store,target);entry['subject']=b.get('title') or b.get('snapshot',{}).get('title') or b.get('proposal',{}).get('text','')[:110]
            entry['issue' if target_kind=='bridge-issue' else 'case' if target_kind=='decision-case' else 'intake_case']=target
    elif kind == "demo-delivery-receipt":
        target = "Jira" if body.get("target") == "jira" else "Azure DevOps"
        entry.update(
            category=f"{target} simulation recorded",
            subject=body.get("item_snapshot", {}).get("key", ""),
            detail=body.get("boundary", ""),
            demo_receipt=row["id"],
        )
    if isinstance(entry["actor"], dict):
        entry["actor"] = entry["actor"].get("id")
    return entry


def issue_waiting_since(store, issue, history):
    """Find when the recorded next action began, ignoring unrelated comments."""
    def next_step(body):
        request = body.get("information_request") or {}
        return (body.get("status"), body.get("next_owner"), body.get("next_question"),
                request.get("at") if request.get("status") == "open" else None)

    current = issue["body"]
    step = next_step(current)
    since = current.get("updated_at") or current.get("created_at")
    for event in reversed(history):
        event_body = event["body"]
        if next_step(shared_body(store, event_body["issue"])) != step:
            break
        since = event_body["at"]
    return since
