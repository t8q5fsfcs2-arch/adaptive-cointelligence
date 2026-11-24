"""Read-only team coordination view over explicitly shared workflow records."""

from dataclasses import asdict
from datetime import datetime

from .core import Ref
from .decisions import ACTORS, SCOPE
from .domain import DOMAINS


def recorded_time(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # A date without an offset does not establish a precise elapsed interval.
        return parsed.isoformat() if parsed.tzinfo is not None else None
    except ValueError:
        return None


def team_timeline(workspace, issues):
    """No model, writes, private plans, inferred dependencies or inferred deadlines."""
    store = workspace.store
    kinds = ("project-work-request", "contribution", "project-design-brief",
             "intent-decision", "decision-case", "domain-definition", "project")
    placeholders = ",".join("?" for _ in kinds)
    rows = store.db.execute(f"""
        SELECT r.id, r.revision FROM records r JOIN
          (SELECT id, MAX(revision) AS revision FROM records GROUP BY id) latest
          ON r.id=latest.id AND r.revision=latest.revision
        WHERE r.scope=? AND r.kind IN ({placeholders}) ORDER BY r.rowid
    """, (SCOPE, *kinds))
    shared = [store.read(Ref(row["id"], row["revision"]), {SCOPE}) for row in rows]
    people = {**ACTORS, **workspace.rights.members}
    domains = {}
    definitions = {key: dict(key=key, label=value["label"], members=value["authors"])
                   for key, value in DOMAINS.items()}
    for record in shared:
        if record["kind"] == "domain-definition":
            definitions[record["body"]["key"]] = record["body"]
    for domain in definitions.values():
        for actor in domain.get("members", []):
            domains.setdefault(actor, []).append((domain["key"], domain["label"]))
    items = []

    def add(record, owner, *, title, status, category, start=None, end=None,
            elapsed_since=None, elapsed_label="Pending", delay="", delay_since=None,
            next_action="", detail="", action=None, action_id=None, domain=None,
            milestone=False, closed=False):
        if isinstance(owner, dict):
            owner = owner.get("id")
        person = people.get(owner, {})
        role = person.get("role", "")
        matches = domains.get(owner, [])
        domain_match = next((d for d in matches if domain and d[0].casefold() == domain.casefold()), None)
        if domain_match is None and len(matches) == 1:
            domain_match = matches[0]
        if domain_match:
            team, team_label = "domain:" + domain_match[0], domain_match[1]
        elif domain:
            team, team_label = "domain:" + domain.casefold(), domain
        else:
            team_label = role or ("Owner not assigned" if not owner else "Project team")
            team = "role:" + team_label
        items.append(dict(key=record["ref"].label() + ":" + (owner or "unassigned"),
            ref=asdict(record["ref"]), title=title, category=category, status=status,
            team=team, team_label=team_label, owner=owner,
            owner_name=person.get("name", owner or "Not assigned"),
            start_at=recorded_time(start), end_at=recorded_time(end),
            elapsed_since=recorded_time(elapsed_since), elapsed_label=elapsed_label,
            delay=delay, delay_since=recorded_time(delay_since),
            due_at=None, next_action=next_action, detail=detail,
            milestone=milestone, closed=closed, action=action, action_id=action_id))
        return items[-1]

    linked_reviews = set()
    for issue in issues:
        body = issue["body"]
        if (body.get("linked") or {}).get("kind") == "requirement":
            linked_reviews.add(body["linked"]["ref"]["id"])
        closed = body["status"] == "resolved"
        resolution = body.get("resolution") or {}
        request = body.get("information_request") or {}
        rights = issue.get("rights") or {}
        since = issue.get("waiting_since")
        owner = resolution.get("actor") if closed else body.get("next_owner")
        status = {"open": "Next action", "investigating": "Investigating",
                  "awaiting-decision": "Awaiting decision", "deferred": "Deferred",
                  "resolved": "Resolved"}.get(body["status"], body["status"])
        delay, delay_since = "", None
        if not closed:
            if rights.get("changed"):
                owner, status, since = rights.get("current_decider"), "Decision rights changed", None
                delay = "Decision rights need review"
            elif (rights.get("escalation") or {}).get("status") == "open":
                escalation = rights["escalation"]
                owner, status, since = escalation.get("owner"), "Awaiting escalation response", escalation.get("at")
                delay, delay_since = status, since
            elif request.get("status") == "open":
                owner, status, since = request.get("owner"), "Information requested", request.get("at")
                delay, delay_since = "Waiting for information", since
            elif body["status"] in {"awaiting-decision", "deferred"}:
                delay, delay_since = status, since
        add(issue, owner, title=body["title"], status=status, category="Decisions & Issues",
            start=body.get("created_at") if closed else since,
            end=resolution.get("at") if closed else None,
            elapsed_since=body.get("created_at") if closed else since,
            elapsed_label="Open for" if closed else "Pending", delay=delay,
            delay_since=delay_since, next_action=body.get("next_question") or body.get("question", ""),
            detail=resolution.get("rationale", "") if closed else body.get("consequence", ""),
            action="bridge-open", action_id=issue["ref"].id, closed=closed)

    outputs = {}
    for record in shared:
        if record["kind"] == "contribution" and record["body"].get("work_request"):
            outputs.setdefault(record["body"]["work_request"]["id"], []).append(record)
    for record in shared:
        body, kind = record["body"], record["kind"]
        if kind == "project-work-request":
            accepted, cancelled = body.get("status") == "accepted", body.get("status") == "cancelled"
            released = outputs.get(record["ref"].id, [])
            dates = [recorded_time(r["body"].get("published_at")) for r in released]
            end = min((d for d in dates if d), key=datetime.fromisoformat, default=None)
            since = body.get("accepted_at") if accepted else body.get("at")
            add(record, body.get("recipient"), title=body["title"], category="Working brief",
                status="Cancelled" if cancelled else "Output published" if released else "Accepted" if accepted else "Awaiting acceptance",
                start=since, end=body.get("updated_at") if cancelled else end,
                elapsed_since=since if not released or end else None,
                elapsed_label="Since acceptance" if accepted else "Since request",
                delay="Awaiting acceptance" if not accepted and not cancelled and not released else "",
                delay_since=since if not accepted and not cancelled and not released else None,
                next_action=body.get("expected_output", ""), detail=body.get("objective", ""),
                action="pflow-request", action_id=record["ref"].id,
                domain=body.get("recipient_domain"), closed=cancelled or bool(released))
        elif kind in {"contribution", "project-design-brief"}:
            at = body.get("published_at")
            packet = body.get("packet")
            add(record, body.get("owner"), title=body.get("title") or (body.get("domain", "Domain") + " Working brief"),
                category="Outcomes report" if kind == "contribution" else "Working brief",
                status="Published for review" if kind == "contribution" else "Shared Working brief",
                start=at, end=at, detail="Publication is not approval of a requirement or proof that the underlying gap is resolved.",
                action="packet" if packet else "pflow-shared-brief" if kind == "project-design-brief" else None,
                action_id=f"{packet['id']}|{packet['revision']}" if packet else f"{record['ref'].id}|{record['ref'].revision}",
                domain=body.get("domain"), milestone=True)
        elif kind == "intent-decision" and body.get("disposition") == "publish-for-investigation":
            actor = body.get("actor")
            if isinstance(actor, dict):
                actor = actor.get("id")
            case = body.get("case")
            add(record, actor, title="Business Intent published", category="Business Intent",
                status="Published for investigation", start=body.get("at"), end=body.get("at"),
                detail=body.get("rationale", ""), milestone=True,
                action="intake-case" if case else None, action_id=case["id"] if case else None)
        elif kind == "decision-case" and record["ref"].id not in linked_reviews and body.get("status") in {"pending-review", "deferred"}:
            rights = workspace.rights.status(body, "requirement")
            required = body.get("required_reviews", {})
            pending = []
            for actor, disposition in required.items():
                raw = body.get("reviews", {}).get(actor)
                review = store.read(Ref(**raw), {SCOPE})["body"] if raw else {}
                if review.get("disposition") != disposition:
                    pending.append(actor)
            owners = ([rights.get("current_decider")] if rights.get("changed") else
                      [body.get("next_owner")] if body["status"] == "deferred" else
                      pending or [rights.get("active_decider")])
            for owner in owners:
                add(record, owner, title=body.get("proposal", {}).get("text", "Requirement review")[:200],
                    category="Requirement review", status="Awaiting review" if pending else "Awaiting decision",
                    start=body.get("created_at"), delay="Awaiting review" if pending else "Awaiting decision",
                    detail="Review opening time is recorded. Time assigned to this responder is not recorded.",
                    next_action="Review the proposal and its governing context.", action="case", action_id=record["ref"].id)
    origin = next((recorded_time(record["body"].get("created_at")) for record in shared
                   if record["kind"] == "project"), None)
    from .timeline_connections import timeline_connections
    connections = timeline_connections(workspace, items, issues, shared, add)
    return dict(items=items, connections=connections, origin_at=origin,
                boundary="Shared workflow records only. Elapsed time is not effort; missing dates and commitments are not inferred.")
