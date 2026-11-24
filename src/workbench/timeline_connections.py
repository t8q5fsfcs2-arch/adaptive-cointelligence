"""Explicit shared handoffs and review/request waits; no inferred dependencies."""

from dataclasses import asdict
import hashlib

from .core import Ref
from .decisions import SCOPE


def timeline_connections(workspace, items, issues, shared, add):
    store, links, seen = workspace.store, [], set()

    def existing(ref, owner=None):
        return next((item for item in items if item["ref"] == ref and
                     (owner is None or item["owner"] == owner)), None)

    def connect(source, target, kind, label, evidence, at=None):
        if not source or not target or source["key"] == target["key"] or source["team"] == target["team"]:
            return
        key = (source["key"], target["key"], kind)
        if key in seen:
            return
        seen.add(key)
        links.append(dict(id=hashlib.sha256(repr(key).encode()).hexdigest()[:16],
            from_key=source["key"], to_key=target["key"], kind=kind, label=label,
            evidence_refs=evidence, at=at))

    for issue in issues:
        body, raw = issue["body"], asdict(issue["ref"])
        if body.get("status") == "resolved" or (issue.get("rights") or {}).get("changed"):
            continue
        request = body.get("information_request") or {}
        if request.get("status") == "open" and request.get("raised_by") and request.get("raised_by") != request.get("owner"):
            responder = existing(raw, request.get("owner"))
            waiter = add(issue, request["raised_by"], title="Information request: " + body["title"],
                category="Information request", status="Awaiting information", start=request.get("at"),
                elapsed_since=request.get("at"), elapsed_label="Request open", delay="Waiting for information",
                delay_since=request.get("at"), next_action=request.get("question", ""),
                detail="This recorded request is open. It does not establish that all other work is blocked.",
                action="bridge-open", action_id=issue["ref"].id)
            waiter["key"] += ":information-wait"
            if responder:
                connect(waiter, responder, "waiting", waiter["owner_name"] + " is awaiting information from " + responder["owner_name"], [raw], request.get("at"))
        linked = body.get("linked") or {}
        if linked.get("kind") != "requirement":
            continue
        case_ref = linked["ref"]
        try:
            case = store.read(Ref(**case_ref), {SCOPE})
            if store.latest(case_ref["id"], {SCOPE})["ref"] != case["ref"]:
                continue
        except PermissionError:
            continue
        cb = case["body"]
        if cb.get("status") != "pending-review":
            continue
        rights = workspace.rights.status(cb, "requirement")
        if rights.get("changed") or rights.get("blockers"):
            continue
        pending = []
        for actor, clearance in cb.get("required_reviews", {}).items():
            review_ref = cb.get("reviews", {}).get(actor)
            review = store.read(Ref(**review_ref), {SCOPE})["body"] if review_ref else None
            if review is None or review.get("disposition") != clearance:
                pending.append((actor, review_ref, review))
        if not pending:
            continue
        decider = rights.get("active_decider") or cb.get("decision_owner")
        current = existing(raw, body.get("next_owner"))
        since = current.get("elapsed_since") if current else None
        waiter = add(case, decider, title="Decision: " + body["title"], category="Required review",
            status="Required reviews outstanding", start=since, elapsed_since=since,
            elapsed_label="Decision waiting", delay="Required review outstanding", delay_since=since,
            next_action="Required review or clearance from: " + ", ".join(workspace.rights.members.get(actor, {}).get("name", actor) for actor, _, _ in pending),
            detail="This decision requires the recorded assessments. The wait applies to this decision, not all project work. Time begins at the recorded current response step; it is not time worked.",
            action="case", action_id=case["ref"].id)
        waiter["key"] += ":decision-wait:" + issue["ref"].id
        for actor, review_ref, review in pending:
            if actor == decider:
                continue
            responder = existing(raw, actor)
            if not responder:
                responder = add(case, actor, title="Review: " + body["title"], category="Required review",
                    status="Required review outstanding" if review is None else "Required clearance not recorded",
                    start=None, elapsed_since=None,
                    detail="The project requires this assessment. Assignment/acceptance time is not recorded; no elapsed ownership interval is assumed.",
                    next_action="Record the required assessment or resolve the existing review disposition.",
                    action="case", action_id=case["ref"].id)
                responder["key"] += ":required-review:" + issue["ref"].id
            evidence = [raw, case_ref] + ([review_ref] if review_ref else [])
            connect(waiter, responder, "waiting", waiter["owner_name"] + " is awaiting " + responder["owner_name"] + "’s required " + ("review" if review is None else "clearance"), evidence, since)

    for record in shared:
        body, ref = record["body"], asdict(record["ref"])
        if record["kind"] == "project-work-request" and body.get("requested_by") and body.get("requested_by") != body.get("recipient"):
            target = existing(ref, body.get("recipient"))
            sent = add(record, body["requested_by"], title="Sent: " + body["title"], category="Working brief handoff",
                status="Work requested", start=body.get("at"), end=body.get("at"), elapsed_since=body.get("at"),
                detail="Recorded sender and recipient. Sending is not acceptance or requirement approval.",
                action="pflow-request", action_id=record["ref"].id, closed=True)
            sent["key"] += ":sent"
            kind = "waiting" if body.get("status") == "requested" else "handoff"
            if body.get("status") != "cancelled":
                connect(sent, target, kind, sent["owner_name"] + (" is awaiting acceptance from " if kind == "waiting" else " handed the Working brief to ") + (target["owner_name"] if target else "the recipient"), [ref], body.get("at"))
        elif record["kind"] == "contribution" and body.get("work_request"):
            source = existing(body["work_request"])
            target = existing(ref)
            if source and target:
                connect(source, target, "handoff", "Published output for the exact Working brief", [body["work_request"], ref], body.get("published_at"))
        elif record["kind"] == "project-design-brief":
            target = existing(ref)
            for basis in body.get("basis", []):
                source = existing(basis)
                if source and source["category"] == "Outcomes report":
                    connect(source, target, "shared-input", source["owner_name"] + "’s report is included in " + target["owner_name"] + "’s Working brief; this does not establish a wait", [basis, ref], body.get("published_at"))
    return links
