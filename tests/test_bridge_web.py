from brief_fixture import complete_design_brief
"""HTTP proof that bridge controls reach the real project services."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import unittest

import test_web
from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.workspace import Workspace
from workbench.model_provider import UnconfiguredModel


class BridgeWebTests(unittest.TestCase):
    def setUp(self):
        self.h=test_web.WebTests();self.h.setUp()
        store=Store(self.h.server.path)
        try:
            owner=Workspace(store,'alex',UnconfiguredModel());owner.setup(dict(title='Synthetic bridge API',intent='Resume work',boundary='Preserve progress'))
            req=owner.create_requirement(dict(title='Resume task',text='Resume the task',rationale='Avoid repetition',drawer='Experience',conditions='Bounded',acceptance_criteria='Observe resumption'))
            self.target=asdict(store.latest(req['id'],{SCOPE})['ref']);self.contributions=[];self.packets=[];self.private=None
            for actor in ('sam','lee'):
                w=Workspace(store,actor,UnconfiguredModel());r=w.command('domain-save',dict(title=actor+' finding',deliverable_type=w.domains.profile()['config']['deliverable_types'][0],observation='A fictional cue helps resumption',source='Synthetic report',limitation='No real evidence evaluated',links=[dict(ref=self.target,relation='supports',rationale='Clarifies resumption')]))
                draft=store.latest(r['id'],w.scopes);complete_design_brief(w,draft);p=w.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='bridge'));handoff=store.latest(p['domainHandoff'],w.scopes)
                self.private=handoff['body']['packet'];released=w.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(handoff['ref']),confirm=True))
                self.contributions.append(asdict(store.latest(released['id'],{SCOPE})['ref']));self.packets.append(released['packet'])
        finally:store.close()
    def tearDown(self):self.h.tearDown()
    def state(self):
        self.h.conn.request('GET','/api/state',headers={'Cookie':self.h.cookie});r=self.h.conn.getresponse();self.assertEqual(r.status,200);return json.loads(r.read())
    def profile(self,actor):self.assertEqual(self.h.post('profile',dict(actor=actor))[0],200)

    def test_issue_review_decision_and_privacy_use_real_http_backend(self):
        self.h.conn.request('GET','/bridge.js');r=self.h.conn.getresponse();self.assertEqual(r.status,200);self.assertIn(b'bridgeScreen',r.read())
        self.profile('sam')
        payload=dict(title='API cue conflict',question='Which cue is supported?',consequence='Avoid repeated work',kind='conflict',boards=['research-design'],owner='sam',route='requirement',target=self.target,requirement_refs=[self.target],packet_refs=self.packets,actor='priya',decision_owner='sam')
        self.assertEqual(self.h.post('bridge-raise',{**payload,'packet_refs':[self.private]})[0],403)
        code,result=self.h.post('bridge-raise',payload);self.assertEqual(code,200);issue=self.state()['bridge']['issues'][0]
        self.assertEqual(issue['body']['created_by'],'sam');self.assertEqual(issue['body']['decision_owner'],'alex')
        self.assertEqual(self.h.post('bridge-close',dict(expected=issue['ref'],confirm=True,rationale='Unauthorized close'))[0],403)
        self.profile('alex')
        code,result=self.h.post('bridge-propose',dict(expected_issue=issue['ref'],text='Show the reviewed cue',rationale='Resolve the supported interaction',acceptance_criteria='Observe successful resumption',conditions='Bounded',selected=self.contributions,changes_intent=False));self.assertEqual(code,200)
        for actor,disposition in [('sam','supported-with-limits'),('lee','cleared-with-conditions')]:
            self.profile(actor);state=self.state();case=state['cases'][0]
            self.assertEqual(self.h.post('review',dict(expected=case['ref'],disposition=disposition,rationale='Synthetic domain response'))[0],200)
        self.profile('alex');case=self.state()['cases'][0]
        self.assertEqual(self.h.post('decision',dict(expected=case['ref'],disposition='approve',rationale='Approve the exact reviewed change',confirm=True))[0],200)
        state=self.state();self.assertEqual(state['bridge']['issues'][0]['body']['status'],'resolved');self.assertEqual(state['bridge']['outcomes'][0]['disposition'],'approve')
        self.assertTrue(any(r['kind']=='requirement' and r['ref']['revision']==2 for r in state['records']))
        timeline=state['bridge']['timeline']['entries'];cursor=state['bridge']['timeline']['before']
        while cursor:
            code,page=self.h.post('project-timeline',dict(before=cursor));self.assertEqual(code,200)
            timeline+=page['entries'];cursor=page['before']
        self.assertEqual(sum(e['category']=='Requirement review opened' for e in timeline),1)
        reviews=[e for e in timeline if e['category']=='Requirement review submitted']
        self.assertEqual({e['actor'] for e in reviews},{'sam','lee'})
        self.assertTrue(all(e['case']['id']==case['ref']['id'] for e in reviews))
        issue=state['bridge']['issues'][0]
        self.assertEqual(next(e['at'] for e in timeline if e['category']=='Issue raised'),issue['body']['created_at'])
        self.assertEqual(next(e['at'] for e in timeline if e['category']=='Requirement approved'),issue['body']['resolution']['at'])



    def test_timeline_uses_shared_dated_versions_and_paginates_without_writing(self):
        store = Store(self.h.server.path)
        try:
            shared_ref = None
            fixture_time = datetime.now(timezone.utc) + timedelta(days=1)
            for i in range(25):
                shared_ref = store.put(f"TIMELINE-{i}", "contribution", SCOPE, {
                    "title": f"Fictional shared work {i}", "domain": "Research",
                    "published_at": fixture_time.isoformat(),
                })
            revised = store.put(shared_ref.id, "contribution", SCOPE, {
                "title": "Revised fictional shared work", "domain": "Research",
                "published_at": (fixture_time + timedelta(days=1)).isoformat(),
            }, shared_ref.revision)
            store.put("PRIVATE-TIMELINE", "contribution", "domain:research", {
                "title": "Private timeline test", "published_at": (fixture_time + timedelta(days=2)).isoformat(),
            })
            before = store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            first = self.state()["bridge"]["timeline"]
            self.assertEqual(first["entries"][0]["ref"], asdict(revised))
            self.assertEqual(first["entries"][1]["ref"], asdict(shared_ref))
            self.assertNotEqual(first["entries"][0]["subject"], first["entries"][1]["subject"])
            code, second = self.h.post("project-timeline", {"before": first["before"]})
            self.assertEqual(code, 200)
            entries = first["entries"] + second["entries"]
            refs = [(item["ref"]["id"], item["ref"]["revision"]) for item in entries]
            self.assertEqual(len(refs), len(set(refs)))
            self.assertEqual(len([item for item in refs if item[0].startswith("TIMELINE-")]), 26)
            self.assertNotIn(("PRIVATE-TIMELINE", 1), refs)
            self.assertEqual(store.db.execute("SELECT COUNT(*) FROM records").fetchone()[0], before)
        finally:
            store.close()

    def test_open_issue_waiting_time_survives_comments_and_follows_reassignment(self):
        self.profile("sam")
        payload = dict(
            title="Fictional timing question", question="Who can check the cue?",
            consequence="Avoid repeated work", kind="question", boards=["research-design"],
            owner="sam", route="coordination", requirement_refs=[self.target], packet_refs=self.packets,
        )
        self.assertEqual(self.h.post("bridge-raise", payload)[0], 200)
        first = self.state()["bridge"]["issues"][0]
        self.assertEqual(first["waiting_since"], first["body"]["created_at"])
        self.assertEqual(self.h.post("bridge-respond", dict(
            expected=first["ref"], action="comment", note="A note about the review."
        ))[0], 200)
        commented = self.state()["bridge"]["issues"][0]
        self.assertEqual(commented["waiting_since"], first["waiting_since"])
        self.assertEqual(self.h.post("bridge-respond", dict(
            expected=commented["ref"], action="assign", note="Assign the next response.",
            next_owner="lee", next_question="Which cue can we test?"
        ))[0], 200)
        state = self.state()["bridge"]
        issue = state["issues"][0]
        self.assertEqual(issue["body"]["next_owner"], "lee")
        self.assertEqual(issue["waiting_since"], issue["body"]["updated_at"])
        events = [e for e in state["timeline"]["entries"] if e.get("issue")]
        self.assertEqual([e["category"] for e in events], ["Issue reassigned", "Issue raised"])
        self.assertEqual(events[-1]["issue"], first["ref"])
