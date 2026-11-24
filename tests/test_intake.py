from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import DecisionBlocked, SCOPE
from workbench.intake import Intake, PRIVATE, VALUE_MODEL, FIT_FIELDS
from workbench.workspace import Workspace


VALUE = dict(beneficiaries="Customers seeking assistance", need="People lose their place after asking for help", value="Complete enrollment with less repeated effort", why_now="A service review is underway", measures="Completion rate; baseline and target to establish", approach="Test a bounded assisted route", evidence="Interview notes supplied by the sponsor; not yet validated", assumptions="A return path will reduce repeated effort; unvalidated", assumption_owner="sam")
VALUE.update(business_challenge="Low completion creates customer effort and avoidable support demand; scale unconfirmed", jobs="Complete enrollment and return after an interruption", gains="Finish confidently without repeating work", job_support="Explore saving and resuming the interrupted step", pain_relievers="Retain entered details to reduce repetition", gain_creators="Show progress and a clear way to continue", supporting_users="Operations colleagues who assist customers")

CONTEXT = dict(in_scope="Guidance and a return path", out_scope="Changing eligibility", constraints="Preserve eligibility checks; no live trial before coverage is confirmed", sources="Eligibility handbook, applicability needs owner review", open_questions="Support demand is not quantified", work_kind="digital", user_situation="A customer switches channels for help, then returns later on a phone", research_question="Which needs recur and what evidence supports them?", operations_question="What support coverage can be offered?")


class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name)/"intake.sqlite3")
        self.sponsor = Intake(self.store,"priya")
        self.sponsor.start({"title":"Enrollment support"})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ref(self):
        return asdict(self.sponsor.draft()["ref"])

    def accept_value(self):
        return self.sponsor.accept_value({'expected':self.ref(),'confirm':True,'rationale':'Reviewed the full proposition and its remaining assumptions'})

    def prepare(self, work_kind="digital", seed=True):
        self.sponsor.save({"expected":self.ref(),"step":"value",**VALUE})
        self.accept_value()
        self.sponsor.save({"expected":self.ref(),"step":"context",**CONTEXT,"work_kind":work_kind})
        self.sponsor.build({"expected":self.ref()})
        if seed:
            drawers = self.sponsor.draft()["body"]["scaffold"]
            drawers[0].update(requirement="A customer can resume after asking for help",acceptance_criteria="Observe resumption in a bounded evaluation")
            self.sponsor.save_drawers({"expected":self.ref(),"drawers":drawers})
        return self.sponsor.request({"expected":self.ref(),"confirm":True})["id"]

    def case_ref(self,id):
        return asdict(self.sponsor.latest(id)["ref"])

    def review(self,id):
        for actor in ("sam","maya"):
            Intake(self.store,actor).review({"expected":self.case_ref(id),"disposition":"ready-for-investigation","rationale":"Proceed with investigation; findings remain unvalidated"})

    def publish(self,id):
        return self.sponsor.publish({"expected":self.case_ref(id),"confirm":True,"rationale":"Investigate the need within the stated limits"})

    def test_value_fit_and_user_situation_travel_into_shared_review_and_intent(self):
        case = self.prepare()
        snapshot = self.sponsor.latest(case)["body"]["snapshot"]
        self.assertEqual(snapshot["value_model"], VALUE_MODEL)
        for key in FIT_FIELDS:
            self.assertEqual(snapshot["values"][key], VALUE[key])
        self.assertIn("jobs", snapshot["scaffold"][0]["value_fit_fields"])
        self.review(case)
        self.publish(case)
        intent = self.sponsor.latest("INT-001")
        self.assertEqual(intent["body"]["fit_status"], "hypothesis-to-test")
        self.assertEqual(intent["body"]["value_proposition"]["gain_creators"], VALUE["gain_creators"])
        self.assertEqual(self.sponsor.latest("CTX-001")["body"]["user_situation"], CONTEXT["user_situation"])
        self.assertEqual(self.sponsor.latest("REQ-INTAKE-needs")["body"]["status"], "proposed")
        self.assertIn(asdict(intent["ref"]), self.store.read_packet("PKT-INTENT", 1, {SCOPE})["refs"])

    def test_new_value_model_requires_explicit_fit_questions_but_allows_unknowns(self):
        self.sponsor.save({"expected": self.ref(), "step": "value", **VALUE, "jobs": ""})
        with self.assertRaises(DecisionBlocked): self.accept_value()
        self.sponsor.save({"expected": self.ref(), "step": "context", **CONTEXT})
        self.sponsor.save({"expected": self.ref(), "step": "value", "jobs": "Unknown: Research will identify the job in interviews"})
        self.accept_value()
        self.sponsor.save({"expected": self.ref(), "step": "context", **CONTEXT})
        self.sponsor.build({"expected": self.ref()})
        self.assertEqual(self.sponsor.draft()["body"]["values"]["business_challenge"], VALUE["business_challenge"])

    def test_legacy_draft_is_preserved_and_requires_review_before_new_progress(self):
        self.sponsor.save({"expected": self.ref(), "step": "value", **VALUE})
        current = self.sponsor.draft(); body = current["body"]
        body.pop("value_model")
        for key in (*FIT_FIELDS, "supporting_users", "user_situation"):
            body["values"].pop(key, None)
        old_ref = self.sponsor.save_draft(current, body)
        with self.assertRaises(DecisionBlocked): self.accept_value()
        state = self.sponsor.state()
        self.assertFalse(state['value_checkpoint']['current'])
        self.assertNotIn('jobs', state['draft']['body']['values'])
        self.sponsor.save({"expected": self.ref(), "step": "value", "value_model": VALUE_MODEL, **VALUE})
        self.accept_value()
        self.sponsor.save({"expected": self.ref(), "step": "context", **CONTEXT})
        self.sponsor.build({"expected": self.ref()})
        self.assertEqual(self.store.read(old_ref, {PRIVATE})['body'], body)
        self.assertIsNone(self.sponsor.latest('INT-001'))

    def test_changing_solution_fit_invalidates_reviews_without_promoting_the_hypothesis(self):
        case = self.prepare()
        self.review(case)
        original = self.sponsor.latest(case)
        self.sponsor.save({"expected": self.ref(), "step": "value", "pain_relievers": "Try a different assistance mechanism"})
        with self.assertRaises(StaleBasis):
            self.publish(case)
        self.assertEqual(self.sponsor.latest(case)["body"]["snapshot"], original["body"]["snapshot"])
        self.assertIsNone(self.sponsor.latest("INT-001"))

    def test_private_intake_is_not_released_by_saving(self):
        self.sponsor.save({"expected":self.ref(),"step":"value",**VALUE})
        state = Workspace(self.store,"sam").state()
        self.assertIsNone(state["intake"]["draft"])
        self.assertEqual(state["intake"]["cases"],[])
        self.assertFalse(any(r["scope"] == PRIVATE for r in state["records"]))
        self.assertEqual(state["packets"],[])
        with self.assertRaises(PermissionError):
            Intake(self.store,"alex").save({"expected":self.ref(),"step":"value",**VALUE})

    def test_partial_saves_allowed_but_complete_basis_needed_to_build(self):
        old=self.ref()
        self.sponsor.save({"expected":old,"step":"value","need":"A new need","assumption_owner":"sam"})
        with self.assertRaises(DecisionBlocked):
            self.sponsor.build({"expected":self.ref()})
        with self.assertRaises(StaleBasis):
            self.sponsor.save({"expected":old,"step":"value",**VALUE})
        with self.assertRaises(ValueError):
            self.sponsor.save({"step":"value",**VALUE})

    def test_profile_aperture_controls_drawers_and_retains_field_provenance(self):
        self.prepare(work_kind="operational",seed=False)
        draft=self.sponsor.draft()["body"]
        self.assertNotIn("technology",[d["key"] for d in draft["scaffold"]])
        needs=draft["scaffold"][0]
        self.assertIn("need",needs["basis_fields"])
        self.assertEqual(needs["requirement"],"")
        self.assertEqual(draft["profile"],asdict(self.sponsor.profile()["ref"]))

    def test_review_release_and_sponsor_decision_have_separate_gates(self):
        id=self.prepare()
        with self.assertRaises(DecisionBlocked): self.publish(id)
        with self.assertRaises(PermissionError):
            Intake(self.store,"alex").publish({"expected":self.case_ref(id),"confirm":True})
        Intake(self.store,"sam").review({"expected":self.case_ref(id),"disposition":"changes-requested","rationale":"Clarify scope"})
        Intake(self.store,"maya").review({"expected":self.case_ref(id),"disposition":"ready-for-investigation","rationale":"Accept investigation"})
        with self.assertRaises(DecisionBlocked): self.publish(id)
        self.review(id)
        with self.assertRaises(ValueError):
            self.sponsor.publish({"expected":self.case_ref(id),"rationale":"Proceed"})
        self.publish(id)
        with self.assertRaises(DecisionBlocked): self.publish(id)

    def test_edit_after_review_requires_fresh_snapshot_and_reviews(self):
        id=self.prepare();self.review(id)
        old_case=self.sponsor.latest(id)
        self.sponsor.save({"expected":self.ref(),"step":"value",**VALUE,"need":"A changed problem"})
        with self.assertRaises(StaleBasis): self.publish(id)
        self.assertEqual(self.sponsor.latest(id)["body"]["snapshot"]["values"]["need"],VALUE["need"])
        self.accept_value()
        self.sponsor.build({"expected":self.ref(),"confirm":True})
        newer=self.sponsor.request({"expected":self.ref(),"confirm":True})["id"]
        self.assertEqual(self.sponsor.latest(newer)["body"]["reviews"],{})
        self.assertTrue(self.sponsor.latest(old_case["ref"].id)["body"]["reviews"])

    def test_profile_change_invalidates_pending_review(self):
        id=self.prepare();self.review(id)
        profile=self.sponsor.profile()
        self.sponsor.configure({"expected":asdict(profile["ref"]),"name":"Adapted domain criteria","drawers":profile["body"]["drawers"]})
        with self.assertRaises(StaleBasis): self.publish(id)
        self.assertFalse(self.sponsor.state()["scaffold_current"])

    def test_atomic_publication_creates_proposed_requirements_and_exact_packets(self):
        id=self.prepare();self.review(id);self.publish(id)
        state=Workspace(self.store,"alex").state()
        drawers = [r for r in state["records"] if r["kind"]=="requirement-drawer"]
        self.assertEqual(len([r for r in drawers if not r['body'].get('parent_id')]),6)
        self.assertEqual(len([r for r in drawers if r['body'].get('parent_id')]),19)
        req=self.sponsor.latest("REQ-INTAKE-needs")
        self.assertEqual(req["body"]["status"],"proposed")
        self.assertEqual(req["body"]["execution"],"not-authorized")
        self.assertEqual(self.sponsor.latest("INT-001")["body"]["status"],"ratified-for-investigation")
        self.assertIn("unvalidated",self.sponsor.latest("INT-001")["body"]["intake"]["assumptions"])
        p=Workspace(self.store,"alex").packet_for(req["ref"])
        self.assertIn(asdict(self.sponsor.latest("DRW-needs")["ref"]),p["refs"])
        for packet in state["packets"]:
            self.assertTrue(all(self.store.read(Ref(**r),{SCOPE}) for r in packet["refs"]))
        self.assertNotIn(PRIVATE,[r["scope"] for r in state["records"]])

    def test_failure_rolls_back_entire_publication(self):
        id=self.prepare();self.review(id)
        count=self.store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
        with patch.object(self.store,"packet",side_effect=RuntimeError("storage failure")):
            with self.assertRaises(RuntimeError): self.publish(id)
        self.assertIsNone(self.sponsor.latest("INT-001"))
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0],count)

    def test_baseline_revision_preserves_approved_work_and_flags_changed_basis(self):
        id=self.prepare();self.review(id);self.publish(id)
        req=self.sponsor.latest("REQ-INTAKE-needs")
        packet=Workspace(self.store,"alex").packet_for(req["ref"])
        # Reconsider the sponsor direction without replacing any existing requirement.
        self.sponsor.save({"expected":self.ref(),"step":"value",**VALUE,"value":"Reduce repeated effort across two channels"})
        self.accept_value()
        self.sponsor.build({"expected":self.ref(),"confirm":True})
        new=self.sponsor.request({"expected":self.ref(),"confirm":True})["id"]
        self.review(new);self.publish(new)
        self.assertEqual(self.sponsor.latest(req["ref"].id)["ref"],req["ref"])
        old=self.store.read_packet(packet["id"],packet["revision"],{SCOPE})
        self.assertIn({"id":"INT-001","revision":1},old["refs"])
        self.assertIn(req["ref"].id,Workspace(self.store,"alex").state()["requirement_impacts"])

    def test_intake_requirement_enters_existing_decision_loop(self):
        id=self.prepare();self.review(id);self.publish(id)
        refs=[]
        for actor in ("sam","maya"):
            w=Workspace(self.store,actor)
            draft=w.save_contribution({"title":"Domain finding","observation":"A return path is needed","source":"Synthetic study","limitation":"Limited evidence"})
            shared=w.publish({"expected":asdict(w.store.latest(draft["id"],w.scopes)["ref"]),"confirm":True})
            refs.append(asdict(self.sponsor.latest(shared["id"])["ref"]))
        w=Workspace(self.store,"alex")
        result=w.submit_proposal({"target":asdict(self.sponsor.latest("REQ-INTAKE-needs")["ref"]),"selected":refs,"text":"Provide a resumable assistance route","rationale":"Supported by the two contributions","acceptance_criteria":"Observe successful resumption","conditions":"Confirm coverage","changes_intent":False})
        for actor,disposition in (("sam","supported-with-limits"),("maya","cleared-with-conditions")):
            Workspace(self.store,actor).review({"expected":asdict(w.loop.case(result["id"])["ref"]),"disposition":disposition,"rationale":"Accept within limits"})
        w.decide({"expected":asdict(w.loop.case(result["id"])["ref"]),"disposition":"approve","rationale":"Approve within conditions","confirm":True})
        self.assertEqual(self.sponsor.latest("REQ-INTAKE-needs")["body"]["status"],"approved")
        self.assertEqual(len(w.state()["decisions"]),1)
        self.assertEqual(len(w.state()["intake"]["decisions"]),1)

    def test_defer_preserves_no_baseline_and_named_next_action(self):
        id=self.prepare()
        self.sponsor.close({"expected":self.case_ref(id),"disposition":"defer","rationale":"Need clarification","next_owner":"maya","next_question":"Confirm coverage boundaries"})
        self.assertIsNone(self.sponsor.latest("INT-001"))
        self.assertEqual(self.sponsor.latest(id)["body"]["next_owner"],"maya")

    def test_existing_project_adopts_intake_without_rewriting_its_work(self):
        legacy = Store(Path(self.tmp.name)/"legacy.sqlite3")
        try:
            owner=Workspace(legacy,"alex")
            owner.setup({"title":"Existing project","intent":"Earlier working intent","boundary":"Preserve rules"})
            reqid=owner.create_requirement({"title":"Earlier requirement","text":"Keep the existing wording","rationale":"Original rationale","acceptance_criteria":"Existing criteria","conditions":"Existing conditions","drawer":"Experience"})["id"]
            old=legacy.latest(reqid,{SCOPE})
            packet=owner.packet_for(old["ref"])
            Intake(legacy,"priya").start({"title":"Existing project"})
            self.assertEqual(legacy.latest(reqid,{SCOPE}),old)
            self.assertEqual(legacy.read_packet(packet["id"],1,{SCOPE}),packet)
            self.assertEqual(legacy.latest("INT-001",{SCOPE})["ref"].revision,1)
            self.assertEqual(Intake(legacy,"priya").draft()["body"]["values"]["value"],"Earlier working intent")
        finally:
            legacy.close()

    def test_new_requirement_uses_active_drawer_and_exact_intent(self):
        id=self.prepare(seed=False);self.review(id);self.publish(id)
        owner=Workspace(self.store,"alex")
        result=owner.create_requirement({"title":"One requirement","text":"A measurable condition","rationale":"A clear reason","acceptance_criteria":"Evaluate the condition","conditions":"Stay within scope","drawer":"Ignored label","drawer_id":"DRW-needs"})
        req=self.sponsor.latest(result["id"])
        self.assertEqual(req["body"]["drawer"],"Customer and user needs")
        self.assertTrue(self.store.graph({SCOPE}).has_edge(req["ref"],self.sponsor.latest("DRW-needs")["ref"]))
        self.assertTrue(self.store.graph({SCOPE}).has_edge(req["ref"],self.sponsor.latest("INT-001")["ref"]))

    def test_requirement_creation_blocked_until_initial_direction_is_published(self):
        with self.assertRaises(DecisionBlocked):
            Workspace(self.store,"alex").create_requirement({})


if __name__ == '__main__': unittest.main()
