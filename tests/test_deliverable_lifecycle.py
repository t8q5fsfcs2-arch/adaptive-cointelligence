"""Real saved-state transitions on synthetic records; no model calls or external writes."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from brief_fixture import complete_design_brief
import test_domain_chat as fixture
from workbench.domain import EDITABLE
from workbench.core import StaleBasis, Store
from workbench.decisions import SCOPE
from workbench.workspace import Workspace


class DeliverableLifecycleTests(unittest.TestCase):
    setUp=fixture.ChatTests.setUp
    tearDown=fixture.ChatTests.tearDown
    start=fixture.ChatTests.start
    draft=fixture.ChatTests.draft

    def authored(self, w=None):
        w=w or self.sam;t=self.start(w)
        d=self.draft(w,t)
        w.command('domain-report-save',dict(conversation=asdict(t['ref']),expected=asdict(d['ref']),
            entries=[dict(id='new-finding',heading='Task recovery',text='Synthetic participants need a recovery path. Scope remains unvalidated.')]))
        return w,t

    def phase(self,w,t):
        return w.domains.state()['deliverables'][self.draft(w,t)['ref'].id]

    def prepare(self,w,t):
        out=w.command('domain-prepare',dict(expected=asdict(self.draft(w,t)['ref']),recipient='bridge'))
        return self.store.latest(out['domainHandoff'],w.scopes)

    def publish(self,w,t,h):
        out=w.command('domain-publish',dict(expected=asdict(self.draft(w,t)['ref']),preflight=asdict(h['ref']),confirm=True))
        return self.store.latest(out['id'],{SCOPE})

    def test_draft_prepare_publish_revise_republish_preserves_history(self):
        w,t=self.authored();original=self.draft(w,t);self.assertEqual(self.phase(w,t)['state'],'draft')
        h=self.prepare(w,t);ready=self.phase(w,t);self.assertEqual(ready['state'],'ready');self.assertEqual(ready['prepared'],asdict(h['ref']))
        published=self.publish(w,t,h);self.assertEqual(self.phase(w,t)['state'],'published');self.assertIsNone(self.phase(w,t)['prepared'])
        w.command('domain-report-save',dict(conversation=asdict(t['ref']),expected=asdict(original['ref']),entries=[dict(id='new-revision',heading='Revised finding',text='A revised, bounded conclusion.')]))
        phase=self.phase(w,t);self.assertEqual(phase['state'],'revising');self.assertEqual(phase['published'],asdict(published['ref']));self.assertTrue(phase['preview_outdated'])
        with self.assertRaises(StaleBasis):self.publish(w,t,h)
        h2=self.prepare(w,t);self.assertEqual(self.phase(w,t)['state'],'ready');new=self.publish(w,t,h2)
        self.assertEqual(new['ref'].revision,published['ref'].revision+1);self.assertEqual(self.phase(w,t)['state'],'published')
        self.assertEqual(self.store.read(published['ref'],{SCOPE}),published)
        self.assertEqual(self.store.read(original['ref'],w.scopes),original)
        self.assertEqual(len(self.model.calls),0)

    def test_requirement_change_invalidates_readiness_and_preserves_publication_fact(self):
        w,t=self.authored();h=self.prepare(w,t);pub=self.publish(w,t,h)
        self.store.put(self.req['ref'].id,'requirement',SCOPE,{**self.req['body'],'text':'Revised criterion for synthetic verification'},self.req['ref'].revision)
        phase=self.phase(w,t);self.assertEqual(phase['state'],'published');self.assertTrue(phase['preview_outdated']);self.assertEqual(phase['published'],asdict(pub['ref']))
        with self.assertRaises(StaleBasis):self.publish(w,t,h)
        self.assertEqual(self.store.latest(pub['ref'].id,{SCOPE}),pub)

    def test_changed_draft_or_domain_configuration_cannot_remain_ready(self):
        w,t=self.authored();self.prepare(w,t);d=self.draft(w,t)
        w.command('domain-save',{**d['body'],'expected':asdict(d['ref']),'title':'Updated synthetic title'})
        phase=self.phase(w,t);self.assertEqual(phase['state'],'draft');self.assertIsNone(phase['prepared']);self.assertTrue(phase['preview_outdated'])
        self.prepare(w,t);profile=w.domains.profile();config={k:deepcopy(profile['config'][k]) for k in EDITABLE};config['descriptor']='Updated synthetic research approach'
        w.domains.configure(dict(domain='research',expected=profile['ref'],config=config,reason='Synthetic test refinement'))
        phase=self.phase(w,t);self.assertEqual(phase['state'],'draft');self.assertTrue(phase['preview_outdated'])

    def test_design_cannot_prepare_until_essential_brief_is_complete(self):
        w,t=self.authored(self.lee);self.assertEqual(self.phase(w,t)['state'],'draft')
        with self.assertRaises(ValueError):self.prepare(w,t)
        self.assertFalse(w.domains.state()['handoffs'])
        complete_design_brief(w,self.draft(w,t));h=self.prepare(w,t)
        self.assertEqual(self.phase(w,t)['state'],'ready');pub=self.publish(w,t,h)
        self.assertEqual(self.phase(w,t)['state'],'published');self.assertIn('design_brief',pub['body'])
        self.assertEqual(len(self.model.calls),0)

    def test_projection_is_owned_private_read_only_and_survives_reopen(self):
        w,t=self.authored();self.prepare(w,t);before=list(self.store.db.iterdump());phase=self.phase(w,t)
        self.assertNotIn(self.draft(w,t)['ref'].id,self.lee.domains.state()['deliverables'])
        self.assertEqual(list(self.store.db.iterdump()),before)
        reopened=Store(self.path)
        try:self.assertEqual(Workspace(reopened,'sam').domains.state()['deliverables'][self.draft(w,t)['ref'].id],phase)
        finally:reopened.close()

    def test_older_unused_preview_does_not_override_the_latest_published_packet(self):
        w,t=self.authored();old=self.prepare(w,t)
        result=w.command('domain-prepare',dict(expected=asdict(self.draft(w,t)['ref']),recipient='design',downstream_needs='A newer synthetic handoff'))
        new=self.store.latest(result['domainHandoff'],w.scopes);self.publish(w,t,new)
        # Storage ordering cannot choose a former unused preview over the latest transaction.
        handoffs=[{**old,'current':True},{**new,'current':True}]
        phase=w.domains.deliverable_states(handoffs)[self.draft(w,t)['ref'].id]
        self.assertEqual(phase['state'],'published');self.assertIsNone(phase['prepared'])
        later=w.command('domain-prepare',dict(expected=asdict(self.draft(w,t)['ref']),recipient='bridge',downstream_needs='A later package for a new audience'))
        self.assertEqual(self.phase(w,t)['state'],'ready');self.assertEqual(self.phase(w,t)['prepared']['id'],later['domainHandoff'])
