"""Human-recorded requirement assessments over the real local request path.

All records are synthetic and temporary. The provider deliberately fails if used.
"""
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import unittest

import test_web
from workbench.core import Store, Ref
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.model_provider import UnconfiguredModel


class NoModelCalls(UnconfiguredModel):
    def __init__(self):
        self.calls = 0

    def generate(self, *args, **kwargs):
        self.calls += 1
        raise AssertionError("Human assessment routes must not call a model")


class RequirementAssessmentHTTPTests(unittest.TestCase):
    def setUp(self):
        self.h = test_web.WebTests()
        self.h.setUp()
        self.addCleanup(self.h.tearDown)
        self.model = NoModelCalls()
        self.h.server.model = self.model
        self.store = Store(self.h.server.path)
        self.addCleanup(self.store.close)
        self.requirement = self.store.put("REQ-HTTP", "requirement", SCOPE, {
            "title": "Preserve draft progress",
            "text": "Preserve draft progress after a failed save.",
            "acceptance_criteria": "A failed Save retains the entered answer for retry.",
            "conditions": "Synthetic nonproduction draft-entry investigation.",
            "rationale": "Avoid losing entered work during recoverable failures.",
            "drawer": "Continuity", "status": "proposed",
            "fulfillment": "not-evaluated", "execution": "not-authorized",
        })
        self.source_text = (
            "Investigate draft-entry interruptions with synthetic examples. "
            "Observe retained answer content and a retry in an isolated form. "
            "The intended users are people entering a long draft answer. "
            "Do not connect the investigation to production storage."
        )
        self.source = self.store.put("SOURCE-HTTP", "source", SCOPE, {
            "title": "Synthetic investigation plan", "text": self.source_text,
            "evidence_level": "documentary",
        })
        self.private = self.store.put("SOURCE-PRIVATE", "source", PRIVATE, {
            "title": "Private sponsor material", "text": "PRIVATE-SECRET-HUMAN-INPUT",
            "evidence_level": "documentary",
        })
        self.requirement_before = deepcopy(self.store.read(self.requirement, {SCOPE}))

    def state(self):
        self.h.conn.request("GET", "/api/state", headers={"Cookie": self.h.cookie})
        response = self.h.conn.getresponse()
        self.assertEqual(response.status, 200)
        return json.loads(response.read())

    def records(self):
        return [tuple(row) for row in self.store.db.execute(
            "SELECT id,revision,kind,scope,body FROM records ORDER BY id,revision"
        )]

    def freeze_payload(self):
        return {
            "requirement": asdict(self.requirement), "expected": None,
            "standard": {"id": "REQ-ASSESSMENT-STANDARD", "revision": 1},
            "scope": "Investigate interrupted draft entry in an isolated form",
            "applicability": "People entering a long answer using synthetic nonproduction content",
            "material_conditions": [{
                "key": "progress",
                "source": {"ref": asdict(self.requirement), "field": "text", "quote": "Preserve draft progress"},
                "expected_observation": "Resume retains the complete entered answer",
                "applicability": "Interrupted draft-entry work in an isolated form",
                "required_evidence_level": "documentary",
                "consequence": "Losing the answer requires avoidable repeated entry",
                "dependencies": [],
            }],
            "rationale": "The selected clause identifies the material recovery behavior to examine",
        }

    def freeze(self):
        status, result = self.h.post("requirement-inventory-freeze", self.freeze_payload())
        self.assertEqual(status, 200, result)
        return result["ref"]

    def assessment_payload(self, inventory):
        standard_path = Path(__file__).parents[1] / "src/workbench/config/requirement_assessment_profiles.v1.json"
        standard = json.loads(standard_path.read_text())
        profiles = standard.get("body", standard)["profiles"]
        source = {"ref": asdict(self.source), "field": "text", "quote": self.source_text, "level": "documentary"}
        return {
            "inventory": inventory, "intended_use": "investigation", "expected": None,
            "condition_judgments": [{
                "key": "progress", "status": "missing",
                "rationale": "The selected plan identifies the question but does not supply observed recovery evidence",
                "evidence": [],
            }],
            "use_judgments": [{
                "key": check["key"], "status": "met",
                "rationale": "The retained synthetic plan specifies the users, investigation question, bounded method and nonproduction scope",
                "evidence": [deepcopy(source)],
            } for check in profiles["investigation"]["checks"]],
            "confidence": {
                "level": "low", "claim": "Preserved draft progress after a failed save",
                "scope": "Interrupted entry of a long draft answer",
                "rationale": "The behavior is plausible but no observation currently supports its fulfillment",
                "limits": "Documentary planning only; runtime behavior and business outcome remain untested",
            },
            "next_action": "Investigate draft interruption and recovery with the stated isolated method",
            "rationale": "This human assessment supports bounded investigation without declaring the requirement fulfilled",
            "confirm": True,
        }

    def assert_no_model_or_requirement_change(self):
        self.assertEqual(self.model.calls, 0)
        self.assertEqual(self.store.read(self.requirement, {SCOPE}), self.requirement_before)
        self.assertEqual(self.store.latest(self.requirement.id, {SCOPE})["ref"], self.requirement)

    def test_state_does_not_invent_assessments_or_write_on_read(self):
        before = self.records()
        first, second = self.state(), self.state()
        self.assertIn("requirement_assessments", first)
        self.assertEqual(first["requirement_assessments"], second["requirement_assessments"])
        serialized = json.dumps(first["requirement_assessments"])
        self.assertIn("not-assessed", serialized)
        self.assertIn("not-rated", serialized)
        self.assertNotIn("PRIVATE-SECRET-HUMAN-INPUT", serialized)
        status, item = self.h.post("requirement-assessment-read", {"requirement": asdict(self.requirement)})
        self.assertEqual(status, 200, item)
        self.assertIsNone(item["inventory"])
        self.assertEqual(item["history"], [])
        for use in ("investigation", "prototype", "implementation"):
            self.assertEqual(item["uses"][use]["status"], "not-assessed")
            self.assertEqual(item["uses"][use]["confidence"]["level"], "not-rated")
            self.assertEqual(item["uses"][use]["condition_results"], [])
        self.assertEqual(item["coverage"]["total"], 0)
        self.assertEqual(item["coverage"]["checked"], 0)
        self.assertEqual(self.records(), before)
        self.assert_no_model_or_requirement_change()

    def test_transport_and_destination_guards_apply_before_new_commands(self):
        before = self.records()
        payload = self.freeze_payload()
        for headers, expected in [
            ({"X-CSRF-Token": ""}, 403),
            ({"Origin": "https://unrelated.example"}, 403),
            ({"X-Workbench-Version": "0"}, 409),
            ({"X-Workbench-Project": "unassigned-project"}, 403),
            ({"X-Workbench-Domain": "not-the-active-domain"}, 409),
        ]:
            with self.subTest(headers=headers):
                status, result = self.h.post("requirement-inventory-freeze", payload, headers)
                self.assertEqual(status, expected, result)
        self.assertEqual(self.records(), before)
        self.assert_no_model_or_requirement_change()

    def test_get_cannot_freeze_or_record_an_assessment(self):
        before = self.records()
        for path in ("/api/requirement-inventory-freeze", "/api/requirement-assessment-record"):
            self.h.conn.request("GET", path, headers={"Cookie": self.h.cookie})
            response = self.h.conn.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
        self.assertEqual(self.records(), before)
        self.assert_no_model_or_requirement_change()

    def test_human_record_round_trip_uses_current_request_path_and_preserves_requirement(self):
        inventory = self.freeze()
        status, result = self.h.post("requirement-assessment-record", self.assessment_payload(inventory))
        self.assertEqual(status, 200, result)
        self.assertIn("ref", result)
        before = self.records()
        status, read = self.h.post("requirement-assessment-read", {"requirement": asdict(self.requirement)})
        self.assertEqual(status, 200, read)
        self.assertIn(result["ref"]["id"], json.dumps(read))
        self.assertEqual(self.records(), before)
        self.assert_no_model_or_requirement_change()

    def test_posted_identity_and_status_cannot_impersonate_an_assessor_or_override_checks(self):
        inventory = self.freeze()
        payload = self.assessment_payload(inventory)
        payload.update(actor="alex", principal="forged-account", assessor_type="model", status="suitable")
        payload["use_judgments"][0].update(
            status="missing", rationale="The intended learning question has not yet been specified in the selected basis", evidence=[]
        )
        status, result = self.h.post("requirement-assessment-record", payload)
        self.assertEqual(status, 200, result)
        saved = self.store.read(Ref(**result["ref"]), {SCOPE})["body"]
        self.assertEqual(saved["actor"], "priya")
        self.assertIsNone(saved["principal"])
        self.assertEqual(saved["assessor_type"], "human")
        self.assertEqual(saved["status"], "needs-work")
        self.assert_no_model_or_requirement_change()

    def test_history_and_source_freshness_preserve_prior_judgments_without_regrading(self):
        inventory = self.freeze()
        payload = self.assessment_payload(inventory)
        status, first = self.h.post("requirement-assessment-record", payload)
        self.assertEqual(status, 200, first)
        original = deepcopy(self.store.read(Ref(**first["ref"]), {SCOPE}))
        payload.update(expected=first["ref"], next_action="Observe a failed Save and the retry using synthetic answers")
        status, second = self.h.post("requirement-assessment-record", payload)
        self.assertEqual(status, 200, second)
        self.assertEqual(second["ref"]["id"], first["ref"]["id"])
        self.assertEqual(second["ref"]["revision"], first["ref"]["revision"] + 1)
        self.assertEqual(self.store.read(Ref(**first["ref"]), {SCOPE}), original)
        self.assertEqual(self.h.post("requirement-assessment-record", payload)[0], 409)
        self.store.put("SOURCE-UNRELATED", "source", SCOPE, {"text": "An unrelated synthetic observation"})
        _, unchanged = self.h.post("requirement-assessment-read", {"requirement": asdict(self.requirement)})
        self.assertEqual(unchanged["uses"]["investigation"]["status"], "suitable")
        self.assertEqual(unchanged["uses"]["investigation"]["confidence"]["level"], "low")
        self.store.put(self.source.id, "source", SCOPE, {"text": self.source_text + " The method has changed.", "evidence_level": "documentary"}, self.source.revision)
        before = self.records()
        _, changed = self.h.post("requirement-assessment-read", {"requirement": asdict(self.requirement)})
        use = changed["uses"]["investigation"]
        self.assertEqual(use["status"], "needs-reassessment")
        self.assertEqual(use["confidence"]["level"], "not-rated")
        self.assertTrue(use["stale"])
        self.assertTrue(use["condition_results"][0]["reusable"])
        self.assertTrue(all(not check["current"] for check in use["use_results"]))
        self.assertEqual(len(changed["history"]), 2)
        self.assertEqual(changed["history"][0]["body"]["confidence"]["level"], "low")
        self.assertEqual(self.records(), before)
        self.assertEqual(self.store.read(Ref(**first["ref"]), {SCOPE}), original)
        self.assert_no_model_or_requirement_change()

    def test_private_or_fabricated_evidence_is_rejected_without_partial_saves(self):
        inventory = self.freeze()
        baseline = self.records()
        variants = []
        private = self.assessment_payload(inventory)
        private["use_judgments"][0]["evidence"] = [{"ref": asdict(self.private), "field": "text", "quote": "PRIVATE-SECRET-HUMAN-INPUT", "level": "documentary"}]
        variants.append(private)
        absent = self.assessment_payload(inventory)
        absent["use_judgments"][0]["evidence"][0]["ref"] = {"id": "UNAVAILABLE-SOURCE", "revision": 1}
        variants.append(absent)
        fabricated = self.assessment_payload(inventory)
        fabricated["use_judgments"][0]["evidence"][0]["quote"] = "A fabricated observation absent from the retained source"
        variants.append(fabricated)
        promoted = self.assessment_payload(inventory)
        promoted["use_judgments"][0]["evidence"][0]["level"] = "runtime"
        variants.append(promoted)
        for payload in variants:
            with self.subTest(evidence=payload["use_judgments"][0]["evidence"]):
                status, result = self.h.post("requirement-assessment-record", payload)
                self.assertIn(status, (400, 403), result)
                self.assertEqual(self.records(), baseline)
        self.assert_no_model_or_requirement_change()

    def test_inventory_refuses_implicit_overwrite_and_administrator_is_not_an_assessor(self):
        inventory = self.freeze()
        before = self.records()
        self.assertEqual(self.h.post("requirement-inventory-freeze", self.freeze_payload())[0], 409)
        self.assertEqual(self.h.post("profile", {"actor": "administrator"})[0], 200)
        status, result = self.h.post("requirement-assessment-record", {**self.assessment_payload(inventory), "actor": "alex"})
        self.assertEqual(status, 403, result)
        self.assertEqual(self.records(), before)
        self.assert_no_model_or_requirement_change()


if __name__ == "__main__":
    unittest.main()
