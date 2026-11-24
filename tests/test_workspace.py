from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import DecisionBlocked, SCOPE
from workbench.workspace import Workspace
from workbench.scenario import initialize


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "browser.sqlite3")
        self.owner = Workspace(self.store, "alex")
        self.owner.setup({"title": "Enrollment", "intent": "Enable completion", "boundary": "Preserve eligibility"})
        self.requirement = self.owner.create_requirement({"title": "Resume enrollment", "text": "Users can resume", "rationale": "Avoid repeated effort", "acceptance_criteria": "Observe successful resumption", "conditions": "Eligibility remains", "drawer": "Experience"})["id"]

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def contribution(self, actor, text="Observed need", expected=None):
        w = Workspace(self.store, actor)
        r = w.save_contribution({"title": "Domain position", "observation": text, "source": "Study section 3, dated today", "limitation": "Limited scope", "interpretation": "A gap may exist", "recommendation": "Evaluate a bounded route", "expected": expected})
        return self.store.latest(r["id"], w.scopes)

    def publish(self, actor, draft):
        r = Workspace(self.store, actor).publish({"expected": asdict(draft["ref"]), "confirm": True})
        return self.store.latest(r["id"], {SCOPE})

    def proposal_data(self):
        research = self.publish("sam", self.contribution("sam"))
        operations = self.publish("maya", self.contribution("maya", "Staffing needs confirmation"))
        return {"target": asdict(self.store.latest(self.requirement, {SCOPE})["ref"]),
                "selected": [asdict(research["ref"]), asdict(operations["ref"])],
                "text": "Provide assistance and a return path", "rationale": "Address the observed need",
                "acceptance_criteria": "User can resume in a scoped test", "conditions": "Confirm staffing first", "changes_intent": False}

    def reviews(self, id):
        for actor, disposition in (("sam", "supported-with-limits"), ("maya", "cleared-with-conditions")):
            Workspace(self.store, actor).review({"expected": asdict(self.owner.loop.case(id)["ref"]), "disposition": disposition, "rationale": "Accept within stated limits"})

    def approve(self, id):
        return self.owner.decide({"expected": asdict(self.owner.loop.case(id)["ref"]), "disposition": "approve", "rationale": "Proceed within conditions", "confirm": True})

    def linked_contribution(self, actor="sam", expected=None):
        w = Workspace(self.store, actor)
        result = w.save_contribution({"title": "Resume evidence", "observation": "Some users lost their place", "source": "Study A", "limitation": "Small sample", "requirement_refs": [asdict(self.store.latest(self.requirement, {SCOPE})["ref"])], "expected": expected})
        return self.store.latest(result["id"], w.scopes)

    def test_shared_progress_is_identical_for_every_role_and_never_counts_private_work(self):
        draft = self.linked_contribution()
        for actor in ("priya", "sam", "maya", "alex"):
            progress = Workspace(self.store, actor).state()["requirement_resolution"][self.requirement]
            self.assertEqual(progress["domains"][0]["contributions"], [])
        released = self.publish("sam", draft)
        projections = [Workspace(self.store, a).state()["requirement_resolution"] for a in ("priya", "sam", "maya", "alex")]
        self.assertTrue(all(p == projections[0] for p in projections))
        self.assertEqual(projections[0][self.requirement]["domains"][0]["contributions"], [asdict(released["ref"])])
        self.assertIn("Requirement approval is pending", projections[0][self.requirement]["brief_considerations"])
        self.assertIn((released["ref"], self.store.latest(self.requirement, {SCOPE})["ref"]), self.store.graph({SCOPE}).edges())

    def test_contribution_cannot_link_private_or_stale_requirements(self):
        w = Workspace(self.store, "sam")
        draft = self.contribution("sam")
        data = {"title": "A", "observation": "B", "source": "C", "limitation": "D", "requirement_refs": [asdict(draft["ref"])]}
        with self.assertRaises(PermissionError):
            w.save_contribution(data)
        linked = self.linked_contribution()
        req = self.store.latest(self.requirement, {SCOPE})
        self.store.put(self.requirement, "requirement", SCOPE, req["body"], req["ref"].revision)
        with self.assertRaises(StaleBasis):
            self.publish("sam", linked)
        data["requirement_refs"] = [asdict(req["ref"])]
        with self.assertRaises(StaleBasis):
            w.save_contribution(data)

    def test_shared_progress_distinguishes_review_from_approval_and_later_evidence(self):
        data = self.proposal_data()
        case = self.owner.submit_proposal(data)["id"]
        self.reviews(case)
        progress = self.owner.state()["requirement_resolution"][self.requirement]
        self.assertEqual(progress["domains"][0]["status"], "Review supports proposal")
        self.assertIn("Requirement approval is pending", progress["brief_considerations"])
        self.approve(case)
        progress = self.owner.state()["requirement_resolution"][self.requirement]
        self.assertEqual(progress["brief_considerations"], [])
        self.assertEqual(progress["domains"][0]["status"], "Prior review supports proposal")
        self.publish("sam", self.linked_contribution())
        progress = self.owner.state()["requirement_resolution"][self.requirement]
        self.assertIn("Assess contributions outside the recorded approval basis", progress["brief_considerations"])
        self.assertEqual(self.store.latest(self.requirement, {SCOPE})["body"]["status"], "approved")

    def test_shared_progress_exposes_concerns_and_deferred_next_action(self):
        case = self.owner.submit_proposal(self.proposal_data())["id"]
        Workspace(self.store, "maya").review({"expected": asdict(self.owner.loop.case(case)["ref"]), "disposition": "not-cleared", "rationale": "No coverage confirmed"})
        self.owner.decide({"expected": asdict(self.owner.loop.case(case)["ref"]), "disposition": "defer", "rationale": "Need coverage", "next_owner": "maya", "next_question": "Who will cover the trial?"})
        progress = Workspace(self.store, "sam").state()["requirement_resolution"][self.requirement]
        self.assertEqual(progress["domains"][1]["status"], "Concern needs resolution")
        self.assertEqual(progress["next_owner"], "maya")
        self.assertEqual(progress["next_question"], "Who will cover the trial?")

    def test_authoring_roles_enforced(self):
        with self.assertRaises(PermissionError):
            Workspace(self.store, "sam").create_requirement({})
        with self.assertRaises(PermissionError):
            self.owner.save_contribution({})

    def test_drafts_hidden_from_other_profiles_and_shared_state(self):
        draft = self.contribution("sam")
        for actor in ("maya", "alex"):
            self.assertNotIn(draft["ref"], [r["ref"] for r in Workspace(self.store, actor).state()["records"]])
        with self.assertRaises(PermissionError):
            Workspace(self.store, "maya").publish({"expected": asdict(draft["ref"]), "confirm": True})
        self.assertEqual(self.owner.state()["packets"][0]["refs"].count(asdict(draft["ref"])), 0)

    def test_publication_requires_preview_confirmation_and_current_revision(self):
        draft = self.contribution("sam")
        with self.assertRaises(ValueError):
            Workspace(self.store, "sam").publish({"expected": asdict(draft["ref"])})
        newer = self.contribution("sam", "Revised observation", asdict(draft["ref"]))
        with self.assertRaises(StaleBasis):
            self.publish("sam", draft)
        shared = self.publish("sam", newer)
        self.assertEqual(shared["body"]["observation"], "Revised observation")
        self.assertEqual(shared["scope"], SCOPE)
        with self.assertRaises(DecisionBlocked):
            self.publish("sam", newer)

    def test_cannot_submit_private_or_one_domain_basis(self):
        data = self.proposal_data()
        data["selected"] = data["selected"][:1]
        with self.assertRaises(DecisionBlocked):
            self.owner.submit_proposal(data)
        private = self.contribution("sam")
        data["selected"] = [asdict(private["ref"])]
        with self.assertRaises(PermissionError):
            self.owner.submit_proposal(data)

    def test_full_custom_input_cycle_persists_and_builds_packet(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        self.reviews(id)
        self.assertTrue(self.owner.state()["cases"][0]["ready"])
        self.approve(id)
        requirement = self.store.latest(self.requirement, {SCOPE})
        self.assertEqual(requirement["body"]["text"], data["text"])
        self.assertEqual(requirement["ref"].revision, 2)
        packets = self.owner.state()["packets"]
        self.assertEqual([p["revision"] for p in packets], [2, 1])
        self.assertIn(data["selected"][0], packets[0]["refs"])
        self.assertEqual(requirement["body"]["execution"], "not-authorized")

    def test_revising_proposal_resets_clearances_without_erasing_reviews(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        self.reviews(id)
        old = self.owner.loop.case(id)
        data.update(expected=asdict(old["ref"]), text="A different solution boundary")
        self.owner.submit_proposal(data)
        self.assertEqual(self.owner.loop.case(id)["body"]["reviews"], {})
        self.assertEqual(len(self.store.read(old["ref"], {SCOPE})["body"]["reviews"]), 2)
        with self.assertRaises(DecisionBlocked):
            self.approve(id)

    def test_republished_contribution_marks_review_stale_then_refreshes(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        self.reviews(id)
        draft = Workspace(self.store, "sam").latest_records("contribution-draft")[0]
        revised = self.contribution("sam", "Later evidence changes scope", asdict(draft["ref"]))
        shared = self.publish("sam", revised)
        c = self.owner.state()["cases"][0]
        self.assertTrue(c["stale"])
        self.assertFalse(c["ready"])
        with self.assertRaises(StaleBasis):
            self.approve(id)
        data["selected"][0] = asdict(shared["ref"])
        data["expected"] = asdict(self.owner.loop.case(id)["ref"])
        self.owner.submit_proposal(data)
        self.assertFalse(self.owner.state()["cases"][0]["stale"])
        self.reviews(id)
        self.approve(id)

    def test_new_proposal_removes_retired_basis_from_new_packet_and_edges(self):
        data = self.proposal_data()
        first = self.owner.submit_proposal(data)["id"]
        self.reviews(first)
        self.approve(first)
        retired = Ref(**data["selected"][0])
        replacement = self.publish("sam", self.contribution("sam", "Replacement finding"))
        data["selected"][0] = asdict(replacement["ref"])
        data["target"] = asdict(self.store.latest(self.requirement, {SCOPE})["ref"])
        second = self.owner.submit_proposal(data)["id"]
        self.reviews(second)
        self.approve(second)
        latest = self.store.latest(self.requirement, {SCOPE})["ref"]
        packet = self.owner.packet_for(latest)
        self.assertNotIn(asdict(retired), packet["refs"])
        self.assertFalse(self.store.graph({SCOPE}).has_edge(latest, retired))
        old = self.store.read_packet(packet["id"], 2, {SCOPE})
        self.assertIn(asdict(retired), old["refs"])

    def test_changed_basis_flags_approved_requirement_without_overwriting_it(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        self.reviews(id)
        self.approve(id)
        draft = Workspace(self.store, "sam").latest_records("contribution-draft")[0]
        revision = self.contribution("sam", "New contradictory observation", asdict(draft["ref"]))
        current = self.publish("sam", revision)
        state = self.owner.state()
        self.assertEqual(state["requirement_impacts"][self.requirement][0]["current"], asdict(current["ref"]))
        req = self.store.latest(self.requirement, {SCOPE})
        self.assertEqual(req["ref"].revision, 2)
        self.assertEqual(req["body"]["status"], "approved")

    def test_one_open_case_per_requirement_and_concurrent_revision_guard(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        with self.assertRaises(DecisionBlocked):
            self.owner.submit_proposal(data)
        data["expected"] = asdict(self.owner.loop.case(id)["ref"])
        self.reviews(id)
        with self.assertRaises(StaleBasis):
            self.owner.submit_proposal(data)

    def test_role_cannot_spoof_decision_owner_in_payload(self):
        data = self.proposal_data()
        id = self.owner.submit_proposal(data)["id"]
        self.reviews(id)
        with self.assertRaises(PermissionError):
            Workspace(self.store, "sam").decide({"actor": "alex", "expected": asdict(self.owner.loop.case(id)["ref"]), "disposition": "approve", "confirm": True, "rationale": "Spoof"})

    def test_existing_terminal_database_can_be_read_without_reseeding(self):
        path = Path(self.tmp.name) / "terminal.sqlite3"
        store = Store(path)
        try:
            initialize(store)
            before = store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            state = Workspace(store, "alex").state()
            self.assertTrue(state["initialized"])
            self.assertEqual(len(state["cases"]), 1)
            self.assertEqual(before, store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0])
        finally:
            store.close()


if __name__ == "__main__":
    unittest.main()
