"""Real SQLite/workflow integration with synthetic records; no model or network calls."""
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Ref, StaleBasis, Store
from workbench.decisions import SCOPE
from workbench.source_links import source_references
from workbench.workspace import Workspace


class SourcePacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "existing.sqlite3"
        self.store = Store(self.path)
        self.owner = Workspace(self.store, "alex")
        self.owner.setup({"title": "Synthetic source proof", "intent": "Enable completion", "boundary": "Preserve eligibility"})
        self.req = self.requirement("Experience")
        self.source = self.store.put("SOURCE-1", "source", SCOPE,
                                     {"title": "Research report", "text": "Participants lose their place when pausing.",
                                      "origin": "synthetic-fixture", "retention": "text-snapshot"})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def requirement(self, drawer):
        result = self.owner.create_requirement({"title": "Resume work", "text": "Users can resume",
            "rationale": "Avoid repeated effort", "conditions": "Eligibility remains", "drawer": drawer})
        return self.store.latest(result["id"], {SCOPE})["ref"]

    def draft(self, actor="sam", refs=None, expected=None, include_sources=True):
        w = Workspace(self.store, actor)
        data = {"title": "Finding" if actor == "sam" else "Constraint", "observation": "A return path is needed",
                "source": "Research report", "limitation": "Small sample", "expected": expected}
        if include_sources:
            data["source_refs"] = [asdict(r) for r in (refs if refs is not None else [self.source])]
        result = w.save_contribution(data)
        return self.store.latest(result["id"], w.scopes)

    def publish(self, draft, actor="sam"):
        result = Workspace(self.store, actor).publish({"expected": asdict(draft["ref"]), "confirm": True})
        return self.store.latest(result["id"], {SCOPE})

    def proposal(self, research=None, req=None):
        research = research or self.publish(self.draft())
        operations = self.publish(self.draft("maya", refs=[]), "maya")
        data = {"target": asdict(req or self.req), "selected": [asdict(research["ref"]), asdict(operations["ref"])],
                "text": "Provide a return path", "rationale": "Address the finding", "conditions": "Eligibility remains",
                "acceptance_criteria": "Resume at the saved step in a scoped test", "changes_intent": False}
        return self.owner.submit_proposal(data)["id"]

    def reviews(self, case_id):
        for actor, disposition in (("sam", "supported-with-limits"), ("maya", "cleared-with-conditions")):
            Workspace(self.store, actor).review({"expected": asdict(self.owner.loop.case(case_id)["ref"]),
                "disposition": disposition, "rationale": "Reviewed the exact basis within its limits"})

    def approve(self, case_id):
        return self.owner.decide({"expected": asdict(self.owner.loop.case(case_id)["ref"]),
            "disposition": "approve", "rationale": "Accept within conditions", "confirm": True})

    def revise_source(self):
        return self.store.put(self.source.id, "source", SCOPE,
                              {"text": "Later findings narrow the affected population."}, self.source.revision)

    def test_source_enters_review_basis_and_packet_survives_repository_restart(self):
        original = self.store.read(self.source, {SCOPE})
        published = self.publish(self.draft())
        case = self.proposal(published)
        self.assertIn(asdict(self.source), self.owner.loop.case(case)["body"]["basis"])
        self.assertTrue(self.store.graph({SCOPE}).has_edge(published["ref"], self.source))
        self.reviews(case)
        self.approve(case)
        req = self.store.latest(self.req.id, {SCOPE})["ref"]
        packet = self.owner.packet_for(req)
        resolved = self.store.resolve_packet(packet["id"], packet["revision"], {SCOPE})
        self.assertIn(original, resolved["records"])
        self.assertIn(asdict(self.source), self.owner.loop.history()[0]["body"]["basis"])
        self.assertEqual(self.store.read(self.source, {SCOPE}), original)
        self.store.close()
        self.store = Store(self.path)
        self.assertEqual(resolved, self.store.resolve_packet(packet["id"], packet["revision"], {SCOPE}))

    def test_changed_source_blocks_approval_without_rewriting_requirement(self):
        case = self.proposal()
        self.reviews(case)
        newer = self.revise_source()
        state = self.owner.state()
        self.assertFalse(state["cases"][0]["ready"])
        self.assertIn({"previous": asdict(self.source), "current": asdict(newer)}, state["cases"][0]["stale"])
        with self.assertRaises(StaleBasis):
            self.approve(case)
        self.assertEqual(self.store.latest(self.req.id, {SCOPE})["ref"], self.req)
        self.assertEqual(self.owner.loop.history(), [])

    def test_changed_source_flags_approved_requirement_and_preserves_historical_packet(self):
        case = self.proposal()
        self.reviews(case)
        self.approve(case)
        req = self.store.latest(self.req.id, {SCOPE})
        packet = self.owner.packet_for(req["ref"])
        before = self.store.resolve_packet(packet["id"], packet["revision"], {SCOPE})
        newer = self.revise_source()
        after = self.store.resolve_packet(packet["id"], packet["revision"], {SCOPE})
        self.assertEqual(before["records"], after["records"])
        self.assertIn({"previous": asdict(self.source), "current": asdict(newer)}, after["changed_refs"])
        self.assertEqual(req, self.store.latest(self.req.id, {SCOPE}))
        self.assertIn({"previous": asdict(self.source), "current": asdict(newer)},
                      self.owner.state()["requirement_impacts"][self.req.id])

    def test_private_sources_can_support_private_draft_but_cannot_cross_bridge(self):
        private = self.store.put("PRIVATE-SOURCE", "source", "domain:research", {"text": "Restricted observation"})
        draft = self.draft(refs=[private])
        self.assertTrue(self.store.graph({SCOPE, "domain:research"}).has_edge(draft["ref"], private))
        with self.assertRaises(PermissionError):
            self.publish(draft)
        with self.assertRaises(PermissionError):
            self.draft("maya", refs=[private])
        self.assertEqual(self.owner.latest_records("contribution"), [])
        self.assertNotIn(private, self.store.graph({SCOPE}))

    def test_source_change_between_draft_and_publication_rejects_atomic_release(self):
        draft = self.draft()
        self.revise_source()
        with self.assertRaises(StaleBasis):
            self.publish(draft)
        self.assertEqual(self.owner.latest_records("contribution"), [])
        self.assertEqual(self.store.latest(draft["ref"].id, {SCOPE, "domain:research"}), draft)

    def test_source_change_before_new_proposal_requires_revised_contribution(self):
        published = self.publish(self.draft())
        self.revise_source()
        with self.assertRaises(StaleBasis):
            self.proposal(published)
        self.assertEqual(self.owner.latest_records("decision-case"), [])

    def test_old_client_edit_retains_source_links_and_explicit_empty_list_removes_them(self):
        draft = self.draft()
        edited = self.draft(expected=asdict(draft["ref"]), include_sources=False)
        self.assertEqual(edited["body"]["source_refs"], [asdict(self.source)])
        cleared = self.draft(refs=[], expected=asdict(edited["ref"]))
        self.assertEqual(cleared["body"]["source_refs"], [])
        self.assertEqual(self.store.read(edited["ref"], {SCOPE, "domain:research"})["body"]["source_refs"], [asdict(self.source)])

    def test_manual_citation_remains_unverified_and_is_not_fetched(self):
        draft = self.draft(include_sources=False)
        published = self.publish(draft)
        self.assertEqual(published["body"]["source_refs"], [])
        self.assertEqual(published["body"]["source"], "Research report")
        self.assertNotIn("verified", published["body"])

    def test_one_contribution_and_source_support_multiple_requirement_packets(self):
        published = self.publish(self.draft())
        other_req = self.requirement("Operations")
        for req in (self.req, other_req):
            case = self.proposal(published, req)
            self.reviews(case)
            self.approve(case)
            packet = self.owner.packet_for(self.store.latest(req.id, {SCOPE})["ref"])
            self.assertEqual(packet["refs"].count(asdict(self.source)), 1)
            self.assertEqual(packet["refs"].count(asdict(published["ref"])), 1)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM records WHERE id=?", (self.source.id,)).fetchone()[0], 1)

    def test_resolver_checks_access_and_missing_records_without_falling_back_to_latest(self):
        private = self.store.put("PRIVATE-SOURCE", "source", "domain:research", {"text": "Private"})
        self.store.packet("PRIVATE-PACKET", 1, "Private review", [private], {"domain:research"}, {SCOPE, "domain:research"})
        with self.assertRaises(PermissionError):
            self.store.resolve_packet("PRIVATE-PACKET", 1, {SCOPE})
        self.store.packet("PUBLIC-PACKET", 1, "Public review", [self.source], {SCOPE}, {SCOPE})
        result = self.store.resolve_packet("PUBLIC-PACKET", 1, {SCOPE, "domain:research"})
        self.assertEqual([r["ref"] for r in result["records"]], [self.source])
        self.revise_source()
        with self.store.transaction():
            self.store.db.execute("DELETE FROM records WHERE id=? AND revision=?", (self.source.id, self.source.revision))
        with self.assertRaises(PermissionError):
            self.store.resolve_packet("PUBLIC-PACKET", 1, {SCOPE})

    def test_invalid_source_references_are_rejected_before_draft_is_written(self):
        for values in (None, "SOURCE-1", [{"id": "SOURCE-1"}], [asdict(self.req)],
                       [asdict(self.source)] * 101):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    source_references(self.store, values, {SCOPE})
        with self.assertRaises(PermissionError):
            self.draft(refs=[Ref("MISSING", 1)])
        self.assertEqual(Workspace(self.store, "sam").latest_records("contribution-draft"), [])


if __name__ == "__main__":
    unittest.main()
