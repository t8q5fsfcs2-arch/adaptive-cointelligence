import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Ref, StaleBasis, Store
from workbench.decisions import DecisionBlocked, DecisionLoop, SCOPE
from workbench.scenario import add_follow_up, initialize, latest_case


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "review.sqlite3"
        self.store = Store(self.path)
        self.loop = DecisionLoop(self.store)
        self.initial = initialize(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def case(self):
        return latest_case(self.loop)

    def reviews(self):
        self.loop.review("sam", self.case()["ref"], "supported-with-limits", "Small sample; supports the problem, not prevalence")
        self.loop.review("maya", self.case()["ref"], "cleared-with-conditions", "Coverage must be confirmed before trial")

    def approve(self):
        return self.loop.decide("alex", self.case()["ref"], "approve", "Proceed with the bounded requirement and stated conditions")

    def counts(self):
        return tuple(self.store.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                     for table in ("records", "packets", "dependencies"))

    def packet(self, revision):
        return self.store.read_packet("PKT-BRIDGE-001", revision, {SCOPE})

    def test_fixture_has_no_human_approval(self):
        self.assertEqual(self.loop.history(), [])
        self.assertEqual(self.case()["body"]["reviews"], {})
        self.assertEqual(self.store.latest("REQ-001", {SCOPE})["body"]["status"], "proposed")
        self.assertEqual(initialize(self.store), self.initial)

    def test_missing_reviews_block_approval_without_partial_writes(self):
        before = self.counts()
        with self.assertRaises(DecisionBlocked):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_only_requirement_owner_can_decide(self):
        self.reviews()
        before = self.counts()
        with self.assertRaises(PermissionError):
            self.loop.decide("sam", self.case()["ref"], "approve", "Research wants this")
        self.assertEqual(before, self.counts())

    def test_reviewer_cannot_impersonate_other_role(self):
        for actor, disposition in (("alex", "supported-with-limits"), ("sam", "cleared-with-conditions"), ("unknown", "not-cleared")):
            with self.subTest(actor=actor), self.assertRaises(PermissionError):
                self.loop.review(actor, self.case()["ref"], disposition, "Explanation")

    def test_approval_revises_requirement_packet_and_preserves_history(self):
        old_packet = self.packet(1)
        self.reviews()
        result = self.approve()
        self.assertEqual(result["requirement"], {"id": "REQ-001", "revision": 2})
        req = self.store.read(Ref(**result["requirement"]), {SCOPE})["body"]
        self.assertEqual(req["status"], "approved")
        self.assertEqual(req["fulfillment"], "not-evaluated")
        self.assertEqual(req["execution"], "not-authorized")
        self.assertEqual(req["supersedes"], {"id": "REQ-001", "revision": 1})
        self.assertEqual(self.packet(1), old_packet)
        self.assertIn({"id": "POL-001", "revision": 1}, self.packet(2)["refs"])
        self.assertIn(result["decision"], self.packet(2)["refs"])
        self.assertTrue(self.store.graph({SCOPE}).has_edge(Ref("REQ-001", 2), Ref(**result["decision"])))
        self.assertEqual(len(self.loop.history()), 1)

    def test_negative_domain_review_blocks_approval(self):
        self.reviews()
        self.loop.review("maya", self.case()["ref"], "not-cleared", "Coverage remains infeasible")
        before = self.counts()
        with self.assertRaises(DecisionBlocked):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_insufficient_evidence_blocks_approval(self):
        self.reviews()
        self.loop.review("sam", self.case()["ref"], "needs-more-evidence", "Need an additional observation")
        with self.assertRaises(DecisionBlocked):
            self.approve()

    def test_rejection_records_reason_without_promoting_proposal(self):
        result = self.loop.decide("alex", self.case()["ref"], "reject", "This approach does not address the need")
        self.assertIsNone(result["requirement"])
        self.assertIsNone(result["packet"])
        self.assertEqual(self.store.latest("REQ-001", {SCOPE})["ref"].revision, 1)
        self.assertEqual(self.case()["body"]["status"], "rejected")
        self.assertEqual(self.loop.history()[0]["body"]["rationale"], "This approach does not address the need")
        with self.assertRaises(DecisionBlocked):
            self.loop.review("sam", self.case()["ref"], "supported-with-limits", "Late review")

    def test_defer_requires_owner_and_question_then_can_resume(self):
        before = self.counts()
        with self.assertRaises(ValueError):
            self.loop.decide("alex", self.case()["ref"], "defer", "Need coverage")
        self.assertEqual(before, self.counts())
        self.loop.decide("alex", self.case()["ref"], "defer", "Need coverage", next_owner="maya", next_question="Can Operations staff a bounded trial?")
        self.assertEqual(self.case()["body"]["status"], "deferred")
        self.assertEqual(self.case()["body"]["next_owner"], "maya")
        self.reviews()
        self.approve()
        self.assertEqual([d["body"]["disposition"] for d in self.loop.history()], ["defer", "approve"])
        self.assertNotIn("next_question", self.case()["body"])

    def test_explanation_required_for_review_and_decision(self):
        before = self.counts()
        with self.assertRaises(ValueError):
            self.loop.review("sam", self.case()["ref"], "supported-with-limits", "  ")
        with self.assertRaises(ValueError):
            self.loop.decide("alex", self.case()["ref"], "reject", "")
        self.assertEqual(before, self.counts())

    def test_stale_screen_cannot_submit(self):
        stale = self.case()["ref"]
        self.reviews()
        before = self.counts()
        with self.assertRaises(StaleBasis):
            self.loop.decide("alex", stale, "approve", "Old screen")
        self.assertEqual(before, self.counts())

    def test_changed_evidence_invalidates_prior_clearances(self):
        self.reviews()
        self.store.put("EVD-001", "evidence", SCOPE, {"text": "A new observation"}, 1)
        before = self.counts()
        with self.assertRaises(StaleBasis):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_changed_requirement_blocks_stale_decision(self):
        self.reviews()
        self.store.put("REQ-001", "requirement", SCOPE, {"text": "Another proposal", "status": "proposed"}, 1)
        before = self.counts()
        with self.assertRaises(StaleBasis):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_new_packet_blocks_stale_decision(self):
        self.reviews()
        self.store.packet("PKT-BRIDGE-001", 2, "New assembly", [Ref(**r) for r in self.packet(1)["refs"]], {SCOPE}, {SCOPE})
        before = self.counts()
        with self.assertRaises(StaleBasis):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_repeated_approval_does_not_duplicate_records(self):
        self.reviews()
        self.approve()
        before = self.counts()
        with self.assertRaises(DecisionBlocked):
            self.approve()
        self.assertEqual(before, self.counts())

    def test_packet_failure_rolls_back_entire_approval(self):
        self.reviews()
        before = self.counts()
        case = self.case()
        with patch.object(self.store, "packet", side_effect=RuntimeError("Simulated storage failure")):
            with self.assertRaises(RuntimeError):
                self.approve()
        self.assertEqual(before, self.counts())
        self.assertEqual(self.case(), case)
        self.assertEqual(self.loop.history(), [])
        self.assertEqual(self.store.latest("REQ-001", {SCOPE})["ref"].revision, 1)
        self.approve()  # Same reviewed case can be retried after the failure.

    def test_restart_preserves_decision_and_graph(self):
        self.reviews()
        result = self.approve()
        self.store.close()
        self.store = Store(self.path)
        self.loop = DecisionLoop(self.store)
        self.assertEqual(initialize(self.store)["body"]["status"], "approved")
        self.assertEqual(self.loop.history()[0]["ref"], Ref(**result["decision"]))
        self.assertTrue(self.store.graph({SCOPE}).has_edge(Ref("REQ-001", 2), Ref("POL-001", 1)))

    def test_follow_up_opens_new_review_and_requires_fresh_clearances(self):
        self.reviews()
        self.approve()
        old_packet = self.packet(2)
        new_case = add_follow_up(self.loop)
        self.assertEqual(new_case["body"]["reviews"], {})
        self.assertEqual(self.store.latest("REQ-001", {SCOPE})["ref"], Ref("REQ-001", 2))
        self.assertEqual(self.packet(2), old_packet)
        impact = self.store.latest("IMP-001", {SCOPE})["body"]
        self.assertIn({"id": "REQ-001", "revision": 2}, impact["affected"])
        with self.assertRaises(DecisionBlocked):
            self.approve()
        self.reviews()
        self.approve()
        refs = self.packet(3)["refs"]
        self.assertIn({"id": "EVD-001", "revision": 2}, refs)
        self.assertIn({"id": "POL-001", "revision": 1}, refs)
        self.assertNotIn({"id": "EVD-001", "revision": 1}, refs)
        self.assertIn({"id": "EVD-001", "revision": 1}, self.packet(2)["refs"])
        self.assertEqual(self.store.latest("REQ-001", {SCOPE})["ref"], Ref("REQ-001", 3))
        with self.assertRaises(DecisionBlocked):
            add_follow_up(self.loop)

    def test_intent_change_requires_separate_sponsor_decision(self):
        with self.assertRaises(DecisionBlocked):
            self.loop.propose("sam", Ref("REQ-001", 1), "PKT-BRIDGE-001", 1,
                              "Change business goal", "Criteria", "Conditions", [], changes_intent=True)

    def test_cli_cancel_and_resume_preserve_only_submitted_actions(self):
        command = [sys.executable, "-m", "workbench.review_cli", "--db", str(self.path)]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        result = subprocess.run(command, input="2\n1\nSupports need within limits\n3\n1\nCoverage must be confirmed\n4\napprove\nBounded approach\nCANCEL\nq\n",
                                text=True, capture_output=True, env=env, check=True)
        self.assertIn("Cancelled. No decision saved.", result.stdout)
        self.assertEqual(self.loop.history(), [])
        self.assertEqual(len(self.case()["body"]["reviews"]), 2)
        result = subprocess.run(command, input="4\napprove\nBounded approach\nAPPROVE\n6\nq\n",
                                text=True, capture_output=True, env=env, check=True)
        self.assertIn("REQ-001:v2", result.stdout)
        self.assertIn("Execution: NOT AUTHORIZED", result.stdout)
        self.assertEqual(len(self.loop.history()), 1)


if __name__ == "__main__":
    unittest.main()
