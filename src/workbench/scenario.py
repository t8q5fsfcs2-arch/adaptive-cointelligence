"""Synthetic Research/Operations scenario. No user decisions are prefilled."""
from dataclasses import asdict

from .core import Ref, Store, ImpactWorker
from .decisions import DecisionLoop, DecisionBlocked, SCOPE


def latest_case(loop):
    row = loop.store.db.execute(
        "SELECT id FROM records WHERE kind='decision-case' AND scope=? ORDER BY rowid DESC LIMIT 1", (SCOPE,)
    ).fetchone()
    return loop.case(row["id"]) if row else None


def initialize(store: Store):
    loop = DecisionLoop(store)
    if latest_case(loop):
        return latest_case(loop)
    if store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]:
        raise DecisionBlocked("Use a new decision walkthrough database; this database contains another scenario")
    scope = {SCOPE}
    with store.transaction():
        intent = store.put("INT-001", "intent", SCOPE,
            {"text": "Help eligible customers complete enrollment, including bounded assistance where needed",
             "status": "scenario-baseline", "note": "Fictional fixture; not an actual sponsor approval"})
        policy = store.put("POL-001", "policy", SCOPE,
            {"text": "Assistance must preserve eligibility checks", "status": "scenario-baseline"})
        evidence = store.put("EVD-001", "evidence", SCOPE,
            {"text": "In a fictional study, some customers could not resume enrollment after seeking help",
             "limitation": "Small illustrative sample; no claim of population prevalence"})
        research = store.put("CON-RES-001", "contribution", SCOPE,
            {"domain": "Research", "text": "Provide a clear assisted route and a way to resume",
             "status": "scenario-published-for-review", "evidence": asdict(evidence)})
        operations = store.put("CON-OPS-001", "contribution", SCOPE,
            {"domain": "Operations", "text": "A limited trial is feasible only after coverage is confirmed; no eligibility waiver",
             "status": "scenario-published-for-review"})
        requirement = store.put("REQ-001", "requirement", SCOPE,
            {"text": "Show permitted alternatives and support information", "status": "proposed",
             "fulfillment": "not-evaluated", "execution": "not-authorized"})
        for dependent, basis in [(research, evidence), (requirement, research),
                                  (requirement, operations), (requirement, intent), (requirement, policy)]:
            store.depend(dependent, basis, scope)
        refs = [intent, policy, evidence, research, operations, requirement]
        store.packet("PKT-BRIDGE-001", 1, "Joint review of the enrollment requirement", refs, scope, scope)
        case = loop.propose("sam", requirement, "PKT-BRIDGE-001", 1,
            "Show approved alternatives, a bounded assisted route, and a usable return path",
            "Eligible users can identify the route and resume enrollment in an evaluated trial; record method and limits",
            "Confirm coverage before a live trial; preserve eligibility checks; retain study limitations",
            refs)
        return loop.case(case.id)


def add_follow_up(loop):
    """An explicit user command injects synthetic evidence, not a background monitor."""
    store = loop.store
    case = latest_case(loop)
    if case is None or case["body"]["status"] != "approved":
        raise DecisionBlocked("First approve a requirement, then test later reconsideration")
    with store.transaction():
        old_evidence = store.latest("EVD-001", loop.scopes)["ref"]
        if old_evidence.revision != 1:
            raise DecisionBlocked("Follow-up evidence is already present in this walkthrough; use --new for another run")
        new_evidence = store.put("EVD-001", "evidence", SCOPE,
            {"text": "Fictional follow-up: customers also need help outside staffed hours",
             "limitation": "Availability demand is not yet quantified"}, expected_revision=1)
        impact = ImpactWorker().run(store, old_evidence, new_evidence, loop.scopes)
        impact_ref = store.put("IMP-001", "impact-assessment", SCOPE, impact)
        target = store.latest("REQ-001", loop.scopes)["ref"]
        packet_revision = loop._latest_packet_revision("PKT-BRIDGE-001")
        # Only current business basis records form a new decision basis; prior decisions
        # and reviews remain traceable in historical packets, not recertified as new evidence.
        basis = [store.latest(id, loop.scopes)["ref"] for id in
                 ("INT-001", "POL-001", "EVD-001", "CON-RES-001", "CON-OPS-001", "REQ-001")]
        basis.append(impact_ref)
        new_case = loop.propose("sam", target, "PKT-BRIDGE-001", packet_revision,
            "Show approved alternatives, assistance availability and a return path, including an out-of-hours request option",
            "Users can identify staffed hours, leave a request outside them and resume later; evaluate with representative tasks",
            "Operations must confirm coverage and response commitments before trial; no 24-hour service or eligibility waiver is implied",
            basis)
        return loop.case(new_case.id)
