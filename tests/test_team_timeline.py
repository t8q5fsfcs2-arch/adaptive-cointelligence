from dataclasses import asdict
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.team_timeline import recorded_time, team_timeline
from workbench.workspace import Workspace


class TeamTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "timeline.sqlite3")
        self.work = Workspace(self.store, "alex")

    def tearDown(self):
        self.store.db.close()
        self.tmp.cleanup()

    def issue(self, **changes):
        body = dict(title="Unknown route", status="investigating", next_owner="lee",
                    created_at="2026-11-10T15:00:00Z", next_question="Clarify the fallback",
                    consequence="Preserve accepted ownership", linked=None)
        body.update(changes)
        ref = self.store.put("ISSUE-TIME", "bridge-issue", SCOPE, body)
        return {**self.store.read(ref, {SCOPE}), "waiting_since": "2026-11-12T15:00:00Z", "rights": {}}

    def test_projects_shared_records_only_without_writing_or_touching_private_work(self):
        workspaces = [Workspace(self.store, actor) for actor in ("priya", "sam", "lee", "alex", "maya")]
        self.store.put("REPORT", "contribution", SCOPE, dict(title="Released result", owner="sam", domain="Research", published_at="2026-11-11T15:00:00Z"))
        self.store.put("SECRET", "contribution", "domain:research", dict(title="PRIVATE NEVER RELEASED", owner="sam", published_at="2026-11-11T15:00:00Z"))
        self.store.put("SECRET-DOMAIN", "domain-definition", "domain:research", dict(key="secret", label="PRIVATE DOMAIN", members=["sam"]))
        before = [tuple(row) for row in self.store.db.execute("SELECT * FROM records")]
        results = [team_timeline(workspace, []) for workspace in workspaces]
        self.assertTrue(all(result == results[0] for result in results))
        self.assertNotIn("PRIVATE", json.dumps(results))
        self.assertEqual(before, [tuple(row) for row in self.store.db.execute("SELECT * FROM records")])

    def test_current_responder_and_step_time_do_not_claim_accepted_work_or_overdue(self):
        item = team_timeline(self.work, [self.issue()])["items"][0]
        self.assertEqual((item["owner"], item["team_label"]), ("lee", "Design"))
        self.assertEqual(item["elapsed_since"], "2026-11-12T15:00:00+00:00")
        self.assertEqual(item["elapsed_label"], "Pending")
        self.assertIsNone(item["due_at"])
        self.assertEqual(item["delay"], "")

    def test_information_wait_and_changed_authority_use_the_recorded_responder(self):
        issue = self.issue(information_request=dict(status="open", owner="sam", at="2026-11-13T12:00:00Z"))
        item = team_timeline(self.work, [issue])["items"][0]
        self.assertEqual(item["owner"], "sam")
        self.assertEqual(item["delay"], "Waiting for information")
        self.assertEqual(item["delay_since"], item["elapsed_since"])
        issue["rights"] = dict(changed=True, current_decider="priya")
        item = team_timeline(self.work, [issue])["items"][0]
        self.assertEqual(item["owner"], "priya")
        self.assertIsNone(item["elapsed_since"])
        self.assertIsNone(item["start_at"])

    def test_closed_issue_uses_resolution_actor_and_end_not_today(self):
        issue = self.issue(status="resolved", resolution=dict(actor="alex", at="2026-11-14T12:00:00Z", rationale="Keep gap open separately"))
        item = team_timeline(self.work, [issue])["items"][0]
        self.assertTrue(item["closed"])
        self.assertEqual(item["owner"], "alex")
        self.assertEqual(item["end_at"], "2026-11-14T12:00:00+00:00")

    def test_request_acceptance_and_published_output_are_distinct(self):
        ref = self.store.put("WORK", "project-work-request", SCOPE, dict(title="Investigate routes", recipient="sam", recipient_domain="research", status="requested", at="2026-11-10T12:00:00Z"))
        first = team_timeline(self.work, [])["items"][0]
        self.assertEqual(first["delay"], "Awaiting acceptance")
        body = self.store.read(ref, {SCOPE})["body"]
        body.update(status="accepted", accepted_at="2026-11-12T12:00:00Z")
        self.store.put("WORK", "project-work-request", SCOPE, body, ref.revision)
        second = team_timeline(self.work, [])["items"][0]
        self.assertEqual(second["elapsed_label"], "Since acceptance")
        self.assertEqual(second["delay"], "")
        self.store.put("OUTPUT", "contribution", SCOPE, dict(title="Result", owner="sam", work_request=asdict(ref), published_at="2026-11-13T12:00:00Z"))
        third = next(item for item in team_timeline(self.work, [])["items"] if item["ref"]["id"] == "WORK")
        self.assertTrue(third["closed"])
        self.assertEqual(third["status"], "Output published")
        self.assertEqual(third["end_at"], "2026-11-13T12:00:00+00:00")

    def test_undated_publication_is_not_backfilled_from_other_timestamps(self):
        self.store.put("LEGACY", "contribution", SCOPE, dict(title="Earlier output", owner="sam", at="2026-11-12T12:00:00Z", updated_at="2026-11-15T12:00:00Z"))
        item = team_timeline(self.work, [])["items"][0]
        self.assertIsNone(item["start_at"])
        self.assertTrue(item["milestone"])
        self.assertIn("not approval", item["detail"])
        self.assertIsNone(recorded_time("2026-11-13"))
        self.assertIsNone(recorded_time("not-a-date"))
        self.assertIsNone(recorded_time("2026-11-13T12:00:00"))

    def test_configured_domain_labels_and_named_people_are_used(self):
        self.store.put("DOMAIN", "domain-definition", SCOPE, dict(key="research", label="Customer discovery", members=["sam"]))
        self.store.put("REPORT", "contribution", SCOPE, dict(title="Released result", owner="sam", domain="Research"))
        self.work.rights.members["sam"]["name"] = "Samantha"
        item = team_timeline(self.work, [])["items"][0]
        self.assertEqual((item["team_label"], item["owner_name"]), ("Customer discovery", "Samantha"))

    def test_linked_reviews_are_not_duplicated_and_missing_responder_timing_stays_unknown(self):
        case = self.store.put("CASE", "decision-case", SCOPE, dict(status="pending-review", proposal=dict(text="Clarify ownership"), created_at="2026-11-10T12:00:00Z", required_reviews={"sam": "supported"}, reviews={}))
        item = team_timeline(self.work, [])["items"][0]
        self.assertEqual(item["owner"], "sam")
        self.assertIsNone(item["elapsed_since"])
        issue = self.issue(linked=dict(kind="requirement", ref=asdict(case)))
        view = team_timeline(self.work, [issue])
        self.assertEqual(sum(item["category"] == "Decisions & Issues" for item in view["items"]), 1)
        self.assertFalse(any(item["category"] == "Requirement review" for item in view["items"]))

    def test_required_review_wait_has_named_endpoints_exact_evidence_and_unknown_assignment_time(self):
        case = self.store.put("CASE", "decision-case", SCOPE, dict(status="pending-review", proposal=dict(text="Clarify ownership"), created_at="2026-11-10T12:00:00Z", decision_owner="alex", required_reviews={"lee": "cleared", "sam": "supported"}, reviews={}))
        issue = self.issue(linked=dict(kind="requirement", ref=asdict(case)))
        before = [tuple(row) for row in self.store.db.execute("SELECT * FROM records")]
        view = team_timeline(self.work, [issue])
        links = view["connections"]
        self.assertEqual(len(links), 2)
        self.assertTrue(all(link["kind"] == "waiting" and asdict(case) in link["evidence_refs"] for link in links))
        nodes = {item["key"]: item for item in view["items"]}
        self.assertTrue(all(nodes[link["from_key"]]["owner"] == "alex" for link in links))
        self.assertEqual({nodes[link["to_key"]]["owner"] for link in links}, {"sam", "lee"})
        sam = next(item for item in view["items"] if item["owner"] == "sam")
        self.assertIsNone(sam["elapsed_since"])
        self.assertEqual(before, [tuple(row) for row in self.store.db.execute("SELECT * FROM records")])

    def test_clearance_closes_review_wait_without_interpreting_negative_review_as_missing(self):
        review = self.store.put("REVIEW", "human-review", SCOPE, dict(disposition="blocked"))
        case = self.store.put("CASE", "decision-case", SCOPE, dict(status="pending-review", decision_owner="alex", required_reviews={"lee": "cleared"}, reviews={"lee": asdict(review)}))
        issue = self.issue(linked=dict(kind="requirement", ref=asdict(case)))
        view = team_timeline(self.work, [issue])
        self.assertIn("clearance", view["connections"][0]["label"])
        self.assertIn(asdict(review), view["connections"][0]["evidence_refs"])
        rb = self.store.read(review, {SCOPE})["body"];rb["disposition"] = "cleared"
        approved = self.store.put("REVIEW", "human-review", SCOPE, rb, review.revision)
        cb = self.store.read(case, {SCOPE})["body"];cb["reviews"]["lee"] = asdict(approved)
        updated = self.store.put("CASE", "decision-case", SCOPE, cb, case.revision)
        issue["body"]["linked"]["ref"] = asdict(updated)
        self.assertFalse(team_timeline(self.work, [issue])["connections"])

    def test_open_information_request_connects_requester_and_responder_only_until_answered(self):
        issue = self.issue(information_request=dict(status="open", owner="sam", raised_by="lee", at="2026-11-13T12:00:00Z", question="Which event confirms receipt?"))
        view = team_timeline(self.work, [issue]);self.assertEqual(len(view["connections"]), 1)
        self.assertIn("Mei Chen is awaiting information from Jordan Reyes", view["connections"][0]["label"])
        issue["body"]["information_request"]["status"] = "answered"
        self.assertFalse(team_timeline(self.work, [issue])["connections"])

    def test_only_exact_shared_input_refs_connect_not_similar_requirements_or_free_text(self):
        report = self.store.put("REPORT", "contribution", SCOPE, dict(title="Research", owner="sam", domain="Research", published_at="2026-11-10T12:00:00Z", requirement_refs=[dict(id="REQ", revision=1)]))
        self.store.put("BRIEF", "project-design-brief", SCOPE, dict(owner="lee", domain="Design", published_at="2026-11-11T12:00:00Z", basis=[asdict(report)]))
        view = team_timeline(self.work, []);self.assertEqual(len(view["connections"]), 1)
        self.assertEqual(view["connections"][0]["kind"], "shared-input")
        self.assertIn("does not establish a wait", view["connections"][0]["label"])
        body = self.store.read(report, {SCOPE})["body"]
        self.store.put("REPORT", "contribution", SCOPE, body, report.revision)
        self.assertFalse(team_timeline(self.work, [])["connections"])
