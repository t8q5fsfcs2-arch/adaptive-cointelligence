"""Explicit human decision commands. No LLM calls and no implicit approvals.

Actors are configured local scenario identities, NOT authenticated users. A future
HTTP adapter must resolve the principal server-side, never trust a posted role.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from uuid import uuid4

from .core import Ref, StaleBasis, Store


SCOPE = "project:demo"
ACTORS = {
    "priya": {"name": "Dana Okafor", "role": "Business sponsor"},
    "sam": {"name": "Jordan Reyes", "role": "Research evidence reviewer"},
    "maya": {"name": "Tom Becker", "role": "Operations reviewer (legacy)"},
    "lee": {"name": "Mei Chen", "role": "Design reviewer"},
    "alex": {"name": "Sofia Alvarez", "role": "Requirement owner"},
}


# Administration is an access persona, never a workflow decision identity.
ADMIN_ACTOR = "administrator"
PERSONAS = {**ACTORS, ADMIN_ACTOR: {"name": "Administrator", "role": "Administrator"}}


class DecisionBlocked(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


class DecisionLoop:
    def __init__(self, store: Store, rights=None):
        from .decision_rights import DecisionRights
        self.rights = rights or DecisionRights(store)
        self.store = store
        self.scopes = {SCOPE}

    def _actor(self, actor):
        if actor not in ACTORS:
            raise PermissionError("Unknown local scenario identity")
        return {"id": actor, **ACTORS[actor], **({"name":self.rights.members[actor]["name"]} if actor in self.rights.members else {})}

    def _latest_packet_revision(self, id):
        row = self.store.db.execute("SELECT MAX(revision) FROM packets WHERE id=?", (id,)).fetchone()
        return row[0]

    def propose(self, actor, target: Ref, packet_id, packet_revision, wording,
                acceptance_criteria, conditions, basis, *, changes_intent=False):
        self._actor(actor)
        if changes_intent:
            raise DecisionBlocked("Return to the sponsor: intent changes require a separate decision")
        if not wording.strip() or not acceptance_criteria.strip() or not conditions.strip():
            raise ValueError("Wording, acceptance criteria and conditions are required")
        basis = sorted(set(basis) | {target})
        if len({r.id for r in basis}) != len(basis):
            raise ValueError("The decision basis must select one revision per record")
        with self.store.transaction():
            requirement = self.store.read(target, self.scopes)
            if requirement["kind"] != "requirement":
                raise ValueError("The target must be a requirement")
            packet = self.store.read_packet(packet_id, packet_revision, self.scopes)
            if asdict(target) not in packet["refs"]:
                raise ValueError("The current packet must include the target requirement")
            for ref in basis:
                if self.store.latest(ref.id, self.scopes)["ref"] != ref:
                    raise StaleBasis(f"Review the latest version of {ref.id}")
            if self._latest_packet_revision(packet_id) != packet_revision:
                raise StaleBasis("Review the latest packet")
            body = {"target": asdict(target), "packet_id": packet_id,
                    "packet_revision": packet_revision,
                    "basis": [asdict(r) for r in basis],
                    "proposal": {"text": wording.strip(),
                                 "acceptance_criteria": acceptance_criteria.strip(),
                                 "conditions": conditions.strip()},
                    "decision_owner": "alex", "status": "pending-review",
                    "reviews": {}, "created_by": actor, "created_at": now(),
                    "decision_ids": [], "changes_intent": False}
            body["required_reviews"]={"sam":"supported-with-limits","maya":"cleared-with-conditions"}
            self.rights.bind(body,"requirement")
            return self.store.put("CHG-" + uuid4().hex[:12], "decision-case", SCOPE, body)

    def case(self, case_id):
        record = self.store.latest(case_id, self.scopes)
        if record["kind"] != "decision-case":
            raise ValueError("Expected a decision case")
        return record

    def _open(self, expected_case: Ref):
        case = self.case(expected_case.id)
        if case["ref"] != expected_case:
            raise StaleBasis("This review changed. Reload it before submitting")
        if case["body"]["status"] in {"approved", "rejected"}:
            raise DecisionBlocked("This case is resolved; open a new proposal for further change")
        return case

    def _fresh(self, body):
        for raw in body["basis"]:
            ref = Ref(**raw)
            if self.store.latest(ref.id, self.scopes)["ref"] != ref:
                raise StaleBasis(f"{ref.id} changed; prepare a new comparison before approval")
        if self._latest_packet_revision(body["packet_id"]) != body["packet_revision"]:
            raise StaleBasis("The shared packet changed; prepare a new comparison")

    def review(self, actor, expected_case: Ref, disposition, rationale):
        self._actor(actor)
        options = {"sam": {"supported-with-limits", "needs-more-evidence"},
                   "maya": {"cleared-with-conditions", "not-cleared"},
                   "lee": {"cleared-with-conditions", "not-cleared"}}
        configured=self.rights.current() is not None
        if not configured and (actor not in options or disposition not in options[actor]):
            raise PermissionError("This identity cannot record that review disposition")
        if not rationale.strip():
            raise ValueError("A review explanation is required")
        with self.store.transaction():
            case = self._open(expected_case)
            body = case["body"]
            self.rights.check_review(body,"requirement",actor)
            expected=body.get("required_reviews",{}).get(actor)
            if configured and disposition not in {expected,"needs-more-evidence","not-cleared"}:raise ValueError("Choose a valid assessment disposition")
            if actor not in body.get("required_reviews", {"sam": "supported-with-limits", "maya": "cleared-with-conditions"}):
                raise PermissionError("This role is not a reviewer for this case")
            self._fresh(body)
            review = self.store.put("REV-" + uuid4().hex[:12], "human-review", SCOPE,
                {"case": asdict(expected_case), "actor": self._actor(actor),
                 "disposition": disposition, "rationale": rationale.strip(),
                 "basis_fingerprint": fingerprint(body["basis"]), "at": now(),
                 "boundary": "Evidence/domain review; not requirement approval"})
            body["reviews"][actor] = asdict(review)
            body["status"] = "pending-review"
            return self.store.put(expected_case.id, "decision-case", SCOPE, body, expected_case.revision)

    def decide(self, actor, expected_case: Ref, disposition, rationale,
               *, next_owner=None, next_question=None):
        principal = self._actor(actor)
        if disposition not in {"approve", "reject", "defer"}:
            raise ValueError("Choose approve, reject or defer")
        if not rationale.strip():
            raise ValueError("A decision rationale is required")
        if disposition == "defer" and (next_owner not in ACTORS or not (next_question or "").strip()):
            raise ValueError("Deferral requires a known next owner and a specific next question")
        with self.store.transaction():
            case = self._open(expected_case)
            body = case["body"]
            authority=self.rights.authorize(body,"requirement",actor,approval=disposition=="approve")
            if disposition == "approve":
                from .setup_governance import require_requirement_approval
                require_requirement_approval(self.store, case)
                from .refinements import blockers
                if blockers(self.store, body['target']['id']):
                    raise DecisionBlocked('An intent refinement affecting this requirement is unresolved. Obtain the sponsor response first')
                self._fresh(body)
                required = body.get("required_reviews", {"sam": "supported-with-limits", "maya": "cleared-with-conditions"})
                for reviewer, clearance in required.items():
                    raw = body["reviews"].get(reviewer)
                    if not raw:
                        raise DecisionBlocked(f"Record {ACTORS[reviewer]['name']}'s review first")
                    review = self.store.read(Ref(**raw), self.scopes)["body"]
                    if review["disposition"] != clearance:
                        raise DecisionBlocked(f"Resolve {ACTORS[reviewer]['name']}'s outstanding concern")
                    if review["basis_fingerprint"] != fingerprint(body["basis"]):
                        raise StaleBasis("The review does not cover the decision basis")
            decision_id = "DEC-" + uuid4().hex[:12]
            decision_body = {"case": asdict(expected_case), "actor": principal,
                "disposition": disposition, "rationale": rationale.strip(), "at": now(),
                "basis": body["basis"], "proposal": body["proposal"],
                "reviews": body["reviews"], "next_owner": next_owner if disposition == "defer" else None,
                "next_question": next_question.strip() if disposition == "defer" else None,
                "authority": authority, "boundary": "Requirement decision only; no fulfillment acceptance or execution authorization"}
            new_target = None
            new_packet = None
            if disposition == "approve":
                target = Ref(**body["target"])
                current = self.store.read(target, self.scopes)
                payload = {**current["body"], **body["proposal"], "status": "approved",
                           "fulfillment": "not-evaluated", "execution": "not-authorized",
                           "supersedes": asdict(target), "decision_id": decision_id}
                new_target = self.store.put(target.id, "requirement", SCOPE, payload, target.revision)
                decision_body["result_requirement"] = asdict(new_target)
            decision = self.store.put(decision_id, "decision", SCOPE, decision_body)
            if new_target:
                target = Ref(**body["target"])
                # Browser proposals explicitly select the active basis; legacy cases carry prior references.
                previous = self.store.read_packet(body["packet_id"], body["packet_revision"], self.scopes)
                refs = {} if body.get("explicit_basis") else {r["id"]: Ref(**r) for r in previous["refs"]}
                refs.update({r["id"]: Ref(**r) for r in body["basis"]})
                refs[new_target.id] = new_target
                refs[decision.id] = decision
                for raw in body["reviews"].values():
                    refs[raw["id"]] = Ref(**raw)
                # Retain only the selected active dependencies when the proposal provides an explicit basis.
                basis_map = {r["id"]: Ref(**r) for r in body["basis"]}
                graph = self.store.graph(self.scopes)
                dependencies = set() if body.get("explicit_basis") else {basis_map.get(r.id, r) for r in graph.successors(target)}
                dependencies.update(Ref(**r) for r in body["basis"] if r["id"] != target.id)
                for basis in dependencies:
                    self.store.depend(new_target, basis, self.scopes)
                self.store.depend(new_target, decision, self.scopes)
                new_packet = self.store.packet(body["packet_id"], body["packet_revision"] + 1,
                    "Requirement decision: " + body["proposal"]["text"], refs.values(),
                    previous["audience_scopes"], self.scopes)
                body["result_requirement"] = asdict(new_target)
                body["result_packet"] = {"id": new_packet["id"], "revision": new_packet["revision"]}
            body["status"] = {"approve": "approved", "reject": "rejected", "defer": "deferred"}[disposition]
            body["decision_ids"].append(decision.id)
            if disposition == "defer":
                body["next_owner"] = next_owner
                body["next_question"] = next_question.strip()
            else:
                body.pop("next_owner", None)
                body.pop("next_question", None)
            updated = self.store.put(expected_case.id, "decision-case", SCOPE, body, expected_case.revision)
            return {"case": asdict(updated), "decision": asdict(decision),
                    "requirement": asdict(new_target) if new_target else None,
                    "packet": new_packet}

    def history(self):
        rows = self.store.db.execute("SELECT id,revision FROM records WHERE kind='decision' AND scope=? ORDER BY rowid", (SCOPE,))
        return [self.store.read(Ref(row["id"], row["revision"]), self.scopes) for row in rows]
