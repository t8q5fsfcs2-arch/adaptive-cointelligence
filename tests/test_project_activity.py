"""Verify visibility during a real workflow call using a held synthetic provider."""

from dataclasses import asdict
import http.client
import json
import threading
import unittest

from test_domain_chat import ChatModel
import test_web
from workbench.agent_runs import AgentRun
from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.domain import DomainAgent
from workbench.workspace import Workspace


class ProjectActivityTests(unittest.TestCase):
    def setUp(self):
        self.web = test_web.WebTests()
        self.web.setUp()
        self.model = ChatModel()
        self.web.server.model = self.model

    def tearDown(self):
        self.web.tearDown()

    def activity(self):
        client = http.client.HTTPConnection("127.0.0.1", self.web.server.server_port, timeout=3)
        try:
            client.request("GET", "/api/project-agent-activity?project=original&generation=1")
            result = client.getresponse()
            self.assertEqual(result.status, 200)
            return json.loads(result.read())
        finally:
            client.close()

    def test_shared_activity_is_visible_during_model_work_and_excludes_private_content(self):
        store = Store(self.web.server.path)
        try:
            owner = Workspace(store, "alex")
            owner.setup(dict(title="Fictional collaboration", intent="Preserve progress", boundary="Synthetic example"))
            result = owner.create_requirement(dict(title="Resume work", text="Resume without lost data",
                rationale="Preserve progress", drawer="Experience", acceptance_criteria="Resume at the prior step", conditions="Non-safety"))
            req = asdict(store.latest(result["id"], {SCOPE})["ref"])
            sponsor = Workspace(store, "priya")
            result = sponsor.project_flow.seed_legacy_request( dict(
                title="Investigate task recovery", recipient="sam", objective="Identify where progress is lost",
                expected_output="Bounded evidence", boundaries="Fictional use only",
                local_context="Review the steps in the fictional task",
                requirement_guidance=[dict(ref=req, local_application="Review task recovery", expected_evidence="One observation")],
                packet_refs=[dict(id="PKT-"+req["id"], revision=1)], requirement_refs=[req],
            ))
            researcher = Workspace(store, "sam", self.model)
            request = store.latest(result["id"], {SCOPE})
            researcher.command("work-request-start", dict(expected=asdict(request["ref"])))
            request = store.latest(result["id"], {SCOPE})
            thread = researcher.domain_chat.threads()[0]
            draft = researcher.domain_chat.draft(thread)
            model = DomainAgent("research", self.model)
            private = store.put("PRIVATE-WORK", "project-work-request", "domain:research",
                                dict(title="Private assignment title"))
            # A retained start receipt alone must never report current work.
            AgentRun(store, "sam", model, "domain-coaching", asdict(private),
                     scope="domain:research", instructions="Secret private instructions")
            AgentRun(store, "sam", model, "domain-coaching", None, purpose="evaluation", scope="domain:research")
        finally:
            store.close()

        self.assertEqual(self.web.post("profile", {"actor": "sam"})[0], 200)
        started, release = threading.Event(), threading.Event()

        def hold_provider():
            started.set()
            if not release.wait(12):
                raise AssertionError("Test did not release the provider")

        self.model.during = hold_provider
        finished = []

        def send():
            finished.append(self.web.post("domain-chat-send", dict(
                conversation=asdict(thread["ref"]), expected=asdict(draft["ref"]),
                consent=True, request_id="synthetic-workflow-request", message="Private chat content.",
            )))

        worker = threading.Thread(target=send)
        worker.start()
        try:
            self.assertTrue(started.wait(5))
            snapshot = self.activity()
            self.assertEqual(len(snapshot["active"]), 1)
            row = snapshot["active"][0]
            self.assertEqual(row["agent"], "Research Evidence AI partner")
            self.assertEqual(row["where"], "Research workbench")
            self.assertEqual(row["requester"], "sam")
            self.assertEqual(row["status"], "running")
            self.assertEqual(row["mode"], "simulated")
            self.assertEqual(row["assignment"], dict(ref=asdict(request["ref"]), title=request["body"]["title"]))
            self.assertEqual([item["status"] for item in snapshot["recent"]], ["unknown"])
            self.assertIsNone(snapshot["recent"][0]["assignment"])
            for private_value in ("Private assignment title", "Private chat content.", "Secret private instructions",
                                  "TEST DOUBLE", draft["ref"].id, "RUN-"):
                self.assertNotIn(private_value, json.dumps(snapshot))
        finally:
            release.set()
            worker.join(6)
        self.assertFalse(worker.is_alive())
        self.assertEqual(finished[0][0], 200)
        self.assertIn("chatReport", finished[0][1])
        after = self.activity()
        self.assertFalse(after["active"])
        self.assertEqual(after["recent"][0]["status"], "succeeded")
        self.assertIsNotNone(after["recent"][0]["finished_at"])
