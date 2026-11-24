"""Browser commands over the same versioned store and human decision services.

One local project per database. Local profiles exercise rights, not authentication.
Model assistance is bounded by the AI partner agent; commitments remain explicit.
"""
from dataclasses import asdict
from uuid import uuid4

from .core import Ref, StaleBasis, ImpactWorker
from . import relationships as _relationships  # registers the D014 typed-link extractor
from .knowledge_components import drawers as knowledge_drawers, public_config as knowledge_public_config
from .knowledge_structure import structure_check, packet_contents
from .decisions import ACTORS, PERSONAS, ADMIN_ACTOR, SCOPE, DecisionBlocked, DecisionLoop, now

DOMAINS = {"sam": ("Research", "domain:research"), "maya": ("Operations", "domain:operations"), "lee": ("Design", "domain:design")}


from .validation import required, optional, reference
from .source_links import source_references
from .intake import Intake, PRIVATE
from .resolution import shared_resolution
from .requirement_evidence import evidence_levels
from .readiness import Readiness
from .meaning import Meaning
from .adoption import Adoptions
from .quiet_suggestions import QuietSuggestions
from .refinements import blockers
from .intake_coach import IntakeCoaching
from .requirement_assistant import RequirementAssistance
from .scaffold_tailoring import ScaffoldTailoring
from .agent_runs import monitoring
from .agent_quality import AgentQuality
from .expertise_methods import ExpertiseMethods


from .document_changes import DocumentChanges

from .goals import Goals, linked_records
from .domain import DomainWorkspace, configured_domains, AUTHOR_DOMAINS
from .field_coach import FieldCoach
from .bridge import Bridge
from .sponsor import Sponsor
from .delivery import Delivery
from .design_visual import DesignVisual
from .domain_chat import DomainChat
from .working_report import WorkingReport
from .project_implications import ProjectImplications
from .domain_submission import DomainSubmissions
from .tool_imports import ToolImports
from .prototype_workflow import PrototypeWorkflow
from .flow_export import FlowExport
from .developer_brief import DeveloperBriefs
from .project_flow import ProjectFlow
from .domain_brief import DomainBrief
from .domain_updates import DomainUpdates
from .demo_delivery import DemoDelivery
from .domain_interpretation import DomainInterpretation
from .domain_knowledge import DomainKnowledge
from .decision_rights import DecisionRights
from .need_contexts import NeedContexts
from .knowledge_cards import KnowledgeCards
from .integrity import Integrity
from .integrity_corrections import Corrections
from .decision_review import DecisionReview
from .integrity_gaps import IntegrityGaps
from .requirement_assessments import RequirementAssessments, INTERNAL_KINDS as ASSESSMENT_INTERNAL_KINDS
from .business_assessments import ASSESSMENT_KIND as BUSINESS_ASSESSMENT_KIND, INVENTORY_KIND as BUSINESS_INVENTORY_KIND

class Workspace:
    def __init__(self, store, actor, model=None, principal_id=None, admin=False, domain_key=None, decision_members=None, settings_access=False):
        if actor not in PERSONAS or (actor == ADMIN_ACTOR and not admin):
            raise PermissionError("Unknown or unauthorized local profile")
        self.store, self.actor = store, actor
        store.backfill_relationships()
        self.principal_id = principal_id
        self.is_admin = bool(admin)
        self.settings_admin = bool(admin or settings_access)
        self.rights = DecisionRights(store, actor, principal=principal_id, admin=self.settings_admin, members=decision_members)
        self.readiness = Readiness(self)
        self.loop = DecisionLoop(store, rights=self.rights)
        available=configured_domains(store)
        preferred=AUTHOR_DOMAINS.get(actor) if domain_key is None else domain_key
        self.domain_key=preferred if preferred in available and actor in available[preferred]['authors'] else None
        self.scopes={SCOPE} | ({available[self.domain_key]['scope']} if self.domain_key else {'domain:operations'} if actor=='maya' else set()) | ({PRIVATE} if actor=='priya' else set())
        self.intake = Intake(store, actor, rights=self.rights)
        self.intake.settings_access = bool(settings_access)
        from .uploads import upload_owner
        self.intake.upload_owner = upload_owner(actor, principal_id)
        self.coaching = IntakeCoaching(self.intake, model)
        self.document_changes = DocumentChanges(self.coaching)
        self.requirement_agent = RequirementAssistance(self.intake, model)
        self.goals = Goals(self.intake, model)
        self.scaffold_tailoring = ScaffoldTailoring(self.intake, model)
        self.quality = AgentQuality(self.coaching,self.requirement_agent)
        self.methods = ExpertiseMethods(self.intake)
        self.domains = DomainWorkspace(self, model)
        self.field_coach = FieldCoach(self, model)
        self.bridge = Bridge(self)
        self.integrity = Integrity(self)
        self.integrity_corrections = Corrections(self)
        self.integrity_gaps = IntegrityGaps(self)
        self.requirement_assessments = RequirementAssessments(self)
        self.decision_review = DecisionReview(self)
        self.sponsor = Sponsor(self)
        self.delivery = Delivery(self)
        self.design_visual = DesignVisual(self)
        self.domain_chat = DomainChat(self)
        self.quiet_suggestions = QuietSuggestions(self)
        self.working_report = WorkingReport(self)
        self.implications = ProjectImplications(self)
        self.cards = KnowledgeCards(self)
        self.submissions = DomainSubmissions(self)
        self.tool_imports = ToolImports(self)
        self.prototypes = PrototypeWorkflow(self)
        self.flows = FlowExport(self)
        self.developer_briefs = DeveloperBriefs(self)
        self.project_flow = ProjectFlow(self)
        self.domain_brief = DomainBrief(self)
        self.domain_updates = DomainUpdates(self)
        self.demo_delivery = DemoDelivery(self)
        self.domain_interpretation = DomainInterpretation(self)
        self.domain_knowledge = DomainKnowledge(self)
        self.meaning = Meaning(self)
        self.adoptions = Adoptions(self)
        self.need_contexts = NeedContexts(self)
        from .review_concerns import ReviewConcerns
        self.review_concerns = ReviewConcerns(self)

    def latest_records(self, kind=None):
        # Read large review bodies only after the existing visibility/type filter.
        rows = self.store.db.execute("""SELECT r.id,r.revision,r.kind,r.scope FROM records r JOIN
            (SELECT id,MAX(revision) revision FROM records GROUP BY id) latest
            ON r.id=latest.id AND r.revision=latest.revision ORDER BY r.rowid DESC""")
        records = [self.store.read(Ref(r["id"], r["revision"]), self.scopes)
                for r in rows if r["scope"] in self.scopes and (kind is None or r["kind"] == kind)
                and (kind is not None or r["kind"] not in ASSESSMENT_INTERNAL_KINDS | {BUSINESS_ASSESSMENT_KIND, BUSINESS_INVENTORY_KIND})]
        return [self.delivery.safe_record(r) if r['kind'] == 'delivery-draft' and hasattr(self, 'delivery') else r
                for r in records]

    def owner_only(self):
        if self.actor not in [self.rights.rules("requirement")["decider"], *self.rights.rules("requirement")["delegates"]]:
            raise PermissionError("Use the named requirement decider or an eligible proposal-preparation delegate")

    def setup(self, data):
        self.owner_only()
        title, intent, boundary = (required(data, k) for k in ("title", "intent", "boundary"))
        with self.store.transaction():
            if self.store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]:
                raise DecisionBlocked("This database already contains a project")
            self.store.put("PROJECT-001", "project", SCOPE, {"title": title, "created_at": now()})
            self.store.put("INT-001", "intent", SCOPE, {"text": intent, "status": "working-baseline", "created_by": self.actor})
            self.store.put("POL-001", "policy", SCOPE, {"text": boundary, "status": "user-declared-boundary", "note": "Not independently verified policy"})
        return "Project created. Add a requirement to begin."

    def create_requirement(self, data):
        from .setup_governance import enabled, baseline
        if enabled(self.store) and baseline(self.store):
            raise DecisionBlocked('Propose later requirements through Decisions & Issues and the sponsor response; direct creation cannot change the shared set.')
        self.owner_only()
        if not self.intake.state()["can_create_requirements"]:
            raise DecisionBlocked("Publish the sponsor direction before creating requirements")
        body = {k: required(data, k) for k in ("title", "text", "rationale", "conditions", "drawer")}
        body["acceptance_criteria"] = optional(data, "acceptance_criteria")
        with self.store.transaction():
            bases = [self.store.latest(id, {SCOPE})["ref"] for id in ("INT-001", "POL-001")]
            if data.get("drawer_id"):
                drawer = self.store.latest(data["drawer_id"], {SCOPE})
                if drawer["kind"] != "requirement-drawer" or drawer["body"]["status"] != "active":
                    raise ValueError("Choose an active requirement drawer")
                body.update(drawer_id=drawer["ref"].id, drawer=drawer["body"]["label"])
                bases.append(drawer["ref"])
                gs, ms = linked_records(self.store, drawer['body'].get('goal_refs', []))
                body.update(goal_refs=[asdict(r) for r in gs], measure_refs=[asdict(r) for r in ms])
                bases.extend([*gs, *ms])
            if self.intake.latest("CTX-001"):
                bases.append(self.intake.latest("CTX-001")["ref"])
            body.update(status="proposed", fulfillment="not-evaluated", execution="not-authorized", created_by=self.actor, created_at=now())
            ref = self.store.put("REQ-" + uuid4().hex[:8], "requirement", SCOPE, body)
            for base in bases:
                self.store.depend(ref, base, {SCOPE})
            packet_id = "PKT-" + ref.id
            self.store.packet(packet_id, 1, "Starting requirement for review", [ref, *bases], {SCOPE}, {SCOPE})
        return {"message": "Requirement saved as proposed. It is not approved.", "id": ref.id}

    def save_contribution(self, data):
        original=AUTHOR_DOMAINS.get(self.actor)
        if original and (self.domain_key not in {None,original} or self.actor not in configured_domains(self.store)[original]['authors']):
            raise PermissionError('Use the selected domain workspace to author this contribution')
        if self.actor not in DOMAINS:
            raise PermissionError("Choose Research or Operations to author a contribution")
        domain, scope = DOMAINS[self.actor]
        body = {k: required(data, k) for k in ("title", "observation", "source", "limitation")}
        body.update({k: optional(data, k) for k in ("interpretation", "recommendation")})
        focus = data.get('validation_focus', 'context')
        if focus not in {'problem', 'solution', 'both', 'context'}:
            raise ValueError('Choose what this finding investigates')
        body['validation_focus'] = focus
        body.update(domain=domain, owner=self.actor, text=body["observation"], status="draft", saved_at=now())
        with self.store.transaction():
            expected = reference(data["expected"]) if data.get("expected") else None
            supplied = data.get("requirement_refs", [])
            if not isinstance(supplied, list) or len(supplied) > 100:
                raise ValueError("Choose a bounded set of related requirements")
            linked = sorted(set(reference(r) for r in supplied))
            for req_ref in linked:
                req = self.store.read(req_ref, {SCOPE})
                if req["kind"] != "requirement":
                    raise ValueError("Only project requirements can be linked here")
                if self.store.latest(req_ref.id, {SCOPE})["ref"] != req_ref:
                    raise StaleBasis("A linked requirement changed. Reload and review its current wording")
            body["requirement_refs"] = [asdict(r) for r in linked]
            if expected:
                previous = self.store.read(expected, self.scopes)
                if previous["kind"] != "contribution-draft" or previous["body"]["owner"] != self.actor:
                    raise PermissionError("Only the author can edit this domain draft")
                if previous["body"].get("chassis"):
                    raise DecisionBlocked("Use the domain workspace to edit this deliverable; its review history must be retained")
                body["published_id"] = previous["body"]["published_id"]
            else:
                body["published_id"] = "CON-" + uuid4().hex[:8]
            # Older clients may omit this field; editing must not silently drop lineage.
            raw_sources = data.get("source_refs", previous["body"].get("source_refs", []) if expected else [])
            sources = source_references(self.store, raw_sources, self.scopes)
            body["source_refs"] = [asdict(r) for r in sources]
            ref = self.store.put(expected.id if expected else "DRAFT-" + uuid4().hex[:8], "contribution-draft", scope, body, expected.revision if expected else 0)
            for source in sources:
                self.store.depend(ref, source, self.scopes)
        return {"message": "Domain draft saved. Publish separately to share it for review.", "id": ref.id}

    def publish(self, data):
        expected = reference(data.get("expected"))
        if self.store.read(expected, self.scopes)["body"].get("chassis"):
            return self.domains.publish(data)
        if self.actor=="lee":raise DecisionBlocked("Publish Design work through the workbench with a completed brief and current preflight")
        if data.get("confirm") is not True:
            raise ValueError("Confirm the publication preview first")
        with self.store.transaction():
            draft = self.store.read(expected, self.scopes)
            if draft["kind"] != "contribution-draft" or draft["body"]["owner"] != self.actor:
                raise PermissionError("Only the draft author can publish")
            if self.store.latest(expected.id, self.scopes)["ref"] != expected:
                raise StaleBasis("The draft changed. Preview the latest version")
            body = {k: draft["body"][k] for k in ("title", "observation", "source", "limitation", "interpretation", "recommendation", "text", "domain", "owner")}
            # A private source cannot be released merely by publishing its interpretation.
            sources = source_references(self.store, draft["body"].get("source_refs", []), {SCOPE}, require_current=True)
            body["source_refs"] = [asdict(r) for r in sources]
            body["validation_focus"] = draft["body"].get("validation_focus", "context")
            body["requirement_refs"] = draft["body"].get("requirement_refs", [])
            for raw in body["requirement_refs"]:
                if self.store.latest(raw["id"], {SCOPE})["ref"] != reference(raw):
                    raise StaleBasis("A linked requirement changed. Edit the draft against its current version before publishing")
            id = draft["body"]["published_id"]
            old = next((r for r in self.latest_records("contribution") if r["ref"].id == id), None)
            if old and old["body"].get("draft_revision") == expected.revision:
                raise DecisionBlocked("This draft version is already published")
            body.update(status="published-for-review", published_at=now(), draft_revision=expected.revision)
            ref = self.store.put(id, "contribution", SCOPE, body, old["ref"].revision if old else 0)
            for raw in body["requirement_refs"]:
                self.store.depend(ref, reference(raw), {SCOPE})
            for source in sources:
                self.store.depend(ref, source, {SCOPE})
            if old:
                impact = ImpactWorker().run(self.store, old["ref"], ref, {SCOPE})
                self.store.put("IMP-" + uuid4().hex[:8], "impact-assessment", SCOPE, {**impact, "at": now()})
        return {"message": "Published to Decisions & Issues. Existing decisions are preserved.", "id": ref.id}

    def packet_for(self, requirement):
        latest = {}
        for p in self.store.packet_manifests({SCOPE}):
            if p['id'] not in latest:
                latest[p['id']] = p
        for p in latest.values():
            if asdict(requirement) in p['refs']:
                return p
        raise DecisionBlocked("No current packet contains this requirement")

    def submit_proposal(self, data):
        from .setup_governance import require_requirement_proposal
        require_requirement_proposal(self.store, data)
        self.owner_only()
        if not self.intake.state()["can_create_requirements"]:
            raise DecisionBlocked("Publish the sponsor direction before a requirement review")
        target = reference(data.get("target"))
        selected = data.get("selected", [])
        if not isinstance(selected, list) or len(selected) > 100:
            raise ValueError("Select a bounded set of contributions")
        refs = [reference(r) for r in selected]
        proposal = {k: required(data, k) for k in ("text", "acceptance_criteria", "conditions", "rationale")}
        if data.get("changes_intent") is not False:
            raise DecisionBlocked("Resolve a change to business intent with its sponsor before submitting this requirement")
        with self.store.transaction():
            target_record = self.store.read(target, {SCOPE})
            if target_record["kind"] != "requirement" or self.store.latest(target.id, {SCOPE})["ref"] != target:
                raise StaleBasis("Reload the current requirement")
            domains, sources = set(), set()
            for ref in refs:
                record = self.store.read(ref, {SCOPE})
                if record["kind"] != "contribution":
                    raise ValueError("Choose published contributions, not private drafts")
                if self.store.latest(ref.id, {SCOPE})["ref"] != ref:
                    raise StaleBasis("A selected contribution changed; review its latest version")
                domains.add(record["body"].get("domain"))
                sources.update(source_references(self.store, record["body"].get("source_refs", []), {SCOPE}, require_current=True))
            counterpart = "Design" if "Design" in domains else "Operations"
            if not {"Research", counterpart} <= domains:
                raise DecisionBlocked("Select Research and Design contributions (or the original Operations basis for a legacy case)")
            required_reviews = {"sam": "supported-with-limits", "lee" if counterpart == "Design" else "maya": "cleared-with-conditions"}
            if "Design" in domains and "Operations" in domains:
                required_reviews["maya"] = "cleared-with-conditions"
            packet = self.packet_for(target)
            extra = [self.intake.latest("CTX-001")["ref"]] if self.intake.latest("CTX-001") else []
            if target_record["body"].get("drawer_id"):
                extra.append(self.store.latest(target_record["body"]["drawer_id"], {SCOPE})["ref"])
            link_source = self.store.latest(target_record['body']['drawer_id'], {SCOPE})['body'] if target_record['body'].get('drawer_id') else target_record['body']
            gs, ms = linked_records(self.store, link_source.get('goal_refs', []))
            extra.extend([*gs, *ms])
            extra.extend(self.need_contexts.selected_basis(data.get('need_context_refs', [])))
            proposal.update(goal_refs=[asdict(r) for r in gs], measure_refs=[asdict(r) for r in ms])
            basis = sorted(set([target, *refs, *sources, *extra, *[self.store.latest(id, {SCOPE})["ref"] for id in ("INT-001", "POL-001")]]))
            active = [r for r in self.latest_records("decision-case") if r["body"]["target"]["id"] == target.id and r["body"]["status"] not in {"approved", "rejected"}]
            if data.get("expected"):
                expected = reference(data["expected"])
                case = self.loop._open(expected)
                if case["body"]["target"]["id"] != target.id:
                    raise ValueError("Proposal target mismatch")
                body = case["body"]
                body.update(target=asdict(target), basis=[asdict(r) for r in basis], proposal=proposal, packet_id=packet["id"], packet_revision=packet["revision"], reviews={}, status="pending-review", revised_by=self.actor, revised_at=now(), explicit_basis=True)
                body["required_reviews"] = required_reviews
                self.rights.bind(body,"requirement")
                body["delegation"]=None;body["escalation"]=None
                body.pop("next_owner", None)
                body.pop("next_question", None)
                result = self.store.put(expected.id, "decision-case", SCOPE, body, expected.revision)
            else:
                if active:
                    raise DecisionBlocked("A review is already open for this requirement; revise that proposal")
                result = self.loop.propose(self.actor, target, packet["id"], packet["revision"], proposal["text"], proposal["acceptance_criteria"], proposal["conditions"], basis)
                body = self.loop.case(result.id)["body"]
                body["proposal"].update(proposal)
                body["explicit_basis"] = True
                body["required_reviews"] = required_reviews
                self.rights.bind(body,"requirement")
                result = self.store.put(result.id, "decision-case", SCOPE, body, result.revision)
        return {"message": "Proposal submitted. Both teams must review this exact wording and basis.", "id": result.id}

    def review(self, data):
        ref = self.loop.review(self.actor, reference(data.get("expected")), required(data, "disposition"), required(data, "rationale"))
        return {"message": "Review saved. The requirement has not changed.", "id": ref.id}

    def decide(self, data):
        if data.get("disposition") == "approve" and data.get("confirm") is not True:
            raise ValueError("Confirm approval of the displayed proposal")
        result = self.loop.decide(self.actor, reference(data.get("expected")), required(data, "disposition"), required(data, "rationale"), next_owner=data.get("next_owner"), next_question=data.get("next_question"))
        return {"message": "Decision saved. " + ("New requirement and packet versions created." if result["requirement"] else "Requirement and packet unchanged."), "id": result["case"]["id"]}

    def state(self):
        records = self.latest_records()
        cases = []
        for record in [r for r in records if r["kind"] == "decision-case"]:
            body = record["body"]
            authority = self.rights.status(body,"requirement")
            stale = []
            for raw in body["basis"]:
                latest = self.store.latest(raw["id"], {SCOPE})["ref"]
                if latest != Ref(**raw):
                    stale.append({"previous": raw, "current": asdict(latest)})
            if self.loop._latest_packet_revision(body["packet_id"]) != body["packet_revision"]:
                stale.append({"packet": body["packet_id"]})
            reviews = {actor: self.store.read(Ref(**raw), {SCOPE}) for actor, raw in body["reviews"].items()}
            intent_blockers = blockers(self.store, body["target"]["id"])
            ready = (not intent_blockers and body["status"] not in {"approved", "rejected"} and not stale and not authority["blockers"] and
                     all(reviews.get(a, {}).get("body", {}).get("disposition") == value for a,value in body.get("required_reviews", {"sam":"supported-with-limits","maya":"cleared-with-conditions"}).items()))
            revisions = []
            for row in self.store.db.execute("SELECT revision FROM records WHERE id=? ORDER BY revision DESC", (record["ref"].id,)):
                prior = self.store.read(Ref(record["ref"].id, row["revision"]), {SCOPE})
                prior["reviews"] = {actor: self.store.read(Ref(**raw), {SCOPE}) for actor, raw in prior["body"]["reviews"].items()}
                revisions.append(prior)
            cases.append({**record, "rights": authority, "intent_blockers": intent_blockers, "stale": stale, "reviews": reviews, "ready": ready, "revisions": revisions,
                          "basis_records": [self.store.read(Ref(**raw), {SCOPE}) for raw in body["basis"]],
                          "target_record": self.store.read(Ref(**body["target"]), {SCOPE})})
        packets = [self.store.resolve_packet(p['id'], p['revision'], self.scopes)
                   for p in self.store.packet_manifests(self.scopes)]
        graph = self.store.graph({SCOPE})
        requirement_impacts = {}
        for requirement in [r for r in records if r["kind"] == "requirement"]:
            changed = []
            for basis in graph.successors(requirement["ref"]):
                original = self.store.read(basis, {SCOPE})
                if original["kind"] not in {"contribution", "evidence", "source", "intake-source", "intent", "policy", "project-context", "requirement-drawer", "goal", "success-measure", "need-context"}:
                    continue
                current = self.store.latest(basis.id, {SCOPE})["ref"]
                if current != basis:
                    changed.append({"previous": asdict(basis), "current": asdict(current)})
            if changed:
                requirement_impacts[requirement["ref"].id] = changed
        decisions = self.loop.history()
        areas = knowledge_drawers(records)
        knowledge = dict(config=knowledge_public_config(),
                         structure=structure_check(self.store, records, packets, areas, self.scopes))
        return {"knowledge_system": knowledge, "requirement_assessments": self.requirement_assessments.state(), "integrity_gaps": self.integrity_gaps.state(), "developer_briefs": self.developer_briefs.state(), "decision_rights": self.rights.state(), "domain_knowledge": self.domain_knowledge.state(), "domain_interpretation": self.domain_interpretation.state(), "demo_delivery": self.demo_delivery.state(), "project_flow": self.project_flow.state(), "domain_updates": self.domain_updates.state(), "domain_objectives": self.domain_brief.state(), "sponsor": self.sponsor.state(), "delivery": self.delivery.state(), "bridge": self.bridge.state(), "actor": self.actor, "actors": {**PERSONAS,**{a:dict(name=p["name"],role=p["role"]) for a,p in self.rights.members.items()}}, "records": records, "cases": cases,
                "packets": packets, "decisions": decisions, "requirement_impacts": requirement_impacts,
                "requirement_resolution": shared_resolution(records, cases, requirement_impacts),
                "requirement_evidence": evidence_levels(records), "readiness": self.readiness.state(records), "meaning": self.meaning.state(), "adoptions": self.adoptions.state(), "quiet_suggestions": self.quiet_suggestions.state(),
                "edges": [{"from": asdict(a), "to": asdict(b)} for a, b in graph.edges()],
                "intake": self.intake.state(), "coaching": self.coaching.state(), "document_changes": self.document_changes.state(),
                "domain_chat": self.domain_chat.state(), "design_visual": self.design_visual.state(), "field_guidance": self.field_coach.public_guidance(), "domains": self.domains.state(), "goals": self.goals.state(), "scaffold_tailoring": self.scaffold_tailoring.state(), "requirement_agent": self.requirement_agent.state(), "agent_monitoring": monitoring(self.store,self.actor,admin=self.is_admin), "agent_methods": self.methods.state(), "agent_quality": self.quality.state(),
                "initialized": any(r["kind"] in {"intent", "project"} for r in records)}

    def packet_type_preview(self, data):
        """D014 Rule 5: read-only contents of a packet type for the shared audience."""
        anchor = reference(data.get("anchor"))
        return {"preview": packet_contents(self.store, data.get("type"), anchor, {SCOPE}),
                "message": "Preview only. No packet was issued."}

    def command(self, action, data):
        if action == "work-request-create":
            raise ValueError("Cross-domain work assignment has been removed. Existing Working briefs remain available.")
        from .setup_governance import enable as enable_setup_governance
        actions = {"requirement-inventory-freeze": self.requirement_assessments.freeze, "requirement-assessment-record": self.requirement_assessments.record, "requirement-assessment-read": self.requirement_assessments.read, "field-coach-concern-prepare": self.review_concerns.prepare, "field-coach-concern-publish": self.review_concerns.publish, "setup-governance-enable": lambda d: enable_setup_governance(self.store, self.actor, d), "integrity-mapping-checkpoint": self.integrity_corrections.checkpoint, "integrity-correction-prepare": self.integrity_corrections.prepare, "integrity-correction-run": self.integrity_corrections.run, "integrity-correction-read": self.integrity_corrections.read, "integrity-gap-read": self.integrity_gaps.read, "integrity-gap-source-read": self.integrity_gaps.read_source, "integrity-gap-respond": self.integrity_gaps.respond, "decision-integrity-read": self.decision_review.read, "decision-integrity-recover": self.decision_review.recover, "decision-integrity-send": self.decision_review.send, "integrity-option-response": self.integrity.option_response, "integrity-proposal": self.integrity.proposal, "integrity-declare": self.integrity.declare, "integrity-expression": self.integrity.expression, "integrity-associate": self.integrity.associate, "integrity-preflight": self.integrity.preflight, "integrity-review-read": self.integrity.read_review, "integrity-assess": self.integrity.assess, "integrity-inventory-prepare": self.integrity.prepare_inventory, "integrity-approve-domain": self.integrity.approve_domain, "integrity-attach": self.integrity.attach, "integrity-dispose": self.integrity.dispose, "integrity-reconcile": self.integrity.reconcile, "integrity-promote": self.integrity.promote, "knowledge-card-capture": self.cards.capture, "knowledge-card-save": self.cards.save, "knowledge-card-read": self.cards.read, "knowledge-card-link-read": self.cards.read_link, "need-context-save": self.need_contexts.save, "need-context-packet": self.need_contexts.packet, "developer-brief-open": self.developer_briefs.opened, "developer-brief-save": self.developer_briefs.save, "developer-brief-refresh": self.developer_briefs.refresh, "developer-brief-prepare": self.developer_briefs.prepare, "developer-brief-read": self.developer_briefs.read, "domain-prototype-preview": self.prototypes.preview, "domain-prototype-generate": self.prototypes.generate, "domain-prototype-save": self.prototypes.save, "domain-prototype-stage": self.prototypes.stage, "domain-prototype-send": self.prototypes.send, "domain-flow-save": self.flows.save, "domain-flow-stage": self.flows.stage, "domain-flow-send": self.flows.send, "domain-tool-settings": self.tool_imports.save, "domain-tool-preview": self.tool_imports.preview, "domain-tool-import": self.tool_imports.apply, "domain-submission-read": self.submissions.read_version, "domain-implication-save": self.implications.save, "domain-submission-save": self.submissions.save, "domain-submission-import": self.submissions.import_file, "domain-submission-from-draft": self.submissions.from_draft, "domain-submission-evaluate": self.submissions.evaluate, "domain-submission-edit-evaluation": self.submissions.edit, "domain-submission-prepare": self.submissions.prepare, "domain-alignment-save": self.domain_chat.save_alignment, "domain-findings-save": self.working_report.save_document, "domain-findings-undo": self.working_report.undo_document, "domain-findings-prepare": self.working_report.prepare_document, "decision-rights-save": self.rights.save, "decision-rights-action": self.rights.action, "project-timeline": self.bridge.timeline, "domain-brief-read": self.domain_brief.read_shared, "domain-brief-create": self.domain_brief.create_manual, "domain-brief-refresh-preview": self.domain_brief.refresh_preview, "domain-brief-refresh": self.domain_brief.refresh, "domain-brief-preview": self.domain_brief.preview, "domain-brief-refine-review": self.domain_brief.refine_review, "domain-brief-refine-prepare": self.domain_brief.refine_prepare, "domain-brief-refine-apply": self.domain_brief.refine_apply, "domain-report-read": self.working_report.read_version, "domain-report-add": self.working_report.add, "domain-report-save": self.working_report.save, "domain-add": self.domain_knowledge.add, "domain-update": self.domain_knowledge.update, "domain-knowledge-save": self.domain_knowledge.save, "domain-interpretation-assess": self.domain_interpretation.assess, "domain-interpretation-bridge": self.domain_interpretation.bridge, "demo-delivery-prepare": self.demo_delivery.prepare, "demo-delivery-commit": self.demo_delivery.commit, "project-update-open": self.domain_updates.open, "domain-objectives-suggest": self.domain_brief.suggest, "domain-objectives-save": self.domain_brief.save, "work-request-respond": self.project_flow.respond, "work-request-start": self.project_flow.start, "work-tools-save": self.project_flow.save_tools, "domain-chat-apply": self.domain_chat.apply, "domain-chat-start": self.domain_chat.start, "domain-chat-attach": self.domain_chat.attach, "domain-chat-context": self.domain_chat.set_context, "domain-chat-focus": self.domain_chat.focus, "domain-chat-send": self.domain_chat.send, "domain-chat-recover": self.domain_chat.recover, "design-pdf-attach": self.design_visual.attach, "design-visual-review": self.design_visual.review, "sponsor-save": self.sponsor.save, "sponsor-coach": self.sponsor.coach, "sponsor-apply-advice": self.sponsor.apply_advice, "delivery-prepare": self.delivery.prepare, "delivery-export": self.delivery.export, "bridge-raise": self.bridge.create, "bridge-respond": self.bridge.respond, "bridge-refresh": self.bridge.refresh, "bridge-propose": self.bridge.propose_requirement, "bridge-link-review": self.bridge.link_review, "bridge-intent-propose": self.bridge.propose_intent, "bridge-close": self.bridge.close, "field-coach-check": self.field_coach.check_connections, "field-coach": self.field_coach.run, "domain-configure": self.domains.configure, "domain-source": self.domains.import_source, "domain-save": self.domains.save, "domain-coach": self.domains.review, "domain-apply-advice": self.domains.apply_advice, "domain-prepare": self.domains.prepare, "domain-review": self.domains.review, "domain-disposition": self.domains.disposition, "domain-publish": self.domains.publish, "goals-save": self.goals.save, "readiness-decide": self.readiness.decide, "meaning-propose": self.meaning.propose, "meaning-decide": self.meaning.decide, "meaning-close": self.meaning.close, "enterprise-adopt": self.adoptions.adopt, "enterprise-adoption-drop": self.adoptions.drop, "suggestions-toggle": self.quiet_suggestions.toggle, "suggestions-dismiss": self.quiet_suggestions.dismiss, "goals-prepare": self.goals.run, "goals-apply": self.goals.apply, "scaffold-tailor": self.scaffold_tailoring.run, "scaffold-tailor-apply": self.scaffold_tailoring.apply, "intake-change-assess": self.document_changes.assess, "intake-change-resolve": self.document_changes.resolve,"agent-method-save": self.methods.save, "agent-quality-run": self.quality.run, "agent-quality-review": self.quality.review, "requirement-agent-settings": self.requirement_agent.configure, "requirement-agent-run": self.requirement_agent.run, "requirement-agent-apply": self.requirement_agent.apply, "coach-settings-test": self.coaching.compare_configuration, "agent-descriptor-save": self.coaching.settings.save_agent_descriptor, "coach-settings-save": self.coaching.settings.save_coaching, "coach-settings-preview": self.coaching.preview_instructions, "integration-settings-save": self.coaching.settings.save_connection, "intake-accept-value": self.intake.accept_value, "intake-source": self.coaching.add_source, "intake-coach": self.coaching.run, "intake-coach-apply": self.sponsor.apply_native_advice, "intake-coach-fill-empty": self.coaching.fill_empty, "intent-refine": self.intake.refinements.create, "intent-adopt": self.intake.refinements.adopt, "intent-dispose": self.intake.refinements.dispose, "intake-start": self.intake.start, "intake-save": self.intake.save, "intake-build": self.intake.build, "intake-drawers": self.intake.save_drawers, "intake-preflight": self.intake.prepare_preflight, "intake-request": self.intake.request, "intake-review": self.intake.review, "intake-publish": self.intake.publish, "intake-close": self.intake.close, "intake-configure": self.intake.configure, "setup": self.setup, "requirement": self.create_requirement, "contribution": self.save_contribution,
                   "packet-type-preview": self.packet_type_preview, "publish": self.publish, "proposal": self.submit_proposal, "review": self.review, "decision": self.decide}
        if action not in actions:
            raise ValueError("Unknown action")
        if action in {'decision-rights-action','proposal','review','decision','intent-adopt','intent-dispose','intake-publish','intake-close'}:
            with self.store.transaction():
                self.bridge.guard(action,data)
                result=actions[action](data)
                self.bridge.sync()
                return result
        return actions[action](data)
