"""Evidence sufficiency, classification and exact-claim human review contracts."""
from copy import deepcopy
from dataclasses import asdict
import unittest

import test_domain_development as development
from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench import project_implications as pi

class EvidenceTests(unittest.TestCase):
    setUp=development.DevelopmentTests.setUp
    tearDown=development.DevelopmentTests.tearDown
    start=development.DevelopmentTests.start
    current=development.DevelopmentTests.current
    draft=development.DevelopmentTests.draft
    attach=development.DevelopmentTests.attach
    send=development.DevelopmentTests.send
    data=development.DevelopmentTests.data
    save=development.DevelopmentTests.save
    evaluate=development.DevelopmentTests.evaluate
    def candidate(self,kind='new-requirement',criterion='',support=None):
        p=self.model.implication(self.sam.domain_chat.basis(self.current(self.sam,self.t),self.sam.domain_chat.plan(self.current(self.sam,self.t))[0],purpose='explore')[0])
        p.update(kind=kind,criterion=criterion)
        if kind!='new-requirement':p['targets']=[pi.key(asdict(self.req['ref']))]
        if support is not None:p['support']=support
        original=self.model.implication;self.model.implication=lambda ctx:deepcopy(p)
        try:self.send(self.sam,self.t,request_id='evidence-candidate-'+str(len(self.sam.implications.records(self.current(self.sam,self.t)))))
        finally:self.model.implication=original
        return self.sam.implications.records(self.current(self.sam,self.t))[0]
    def substantive(self):
        return dict(assessment='substantive',basis='Synthetic test only: a permitted source directly supports this bounded claim.',scope='Only the exact scenario and version supplied; no population or runtime conclusion.',corroboration='A fixture authority applies only to this test condition.',counterevidence='Alternate explanations were considered; this test makes no real research claim.',gaps=[])
    def review(self,row,**extra):
        return self.sam.command('domain-implication-save',{**dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held',evidence_review=self.substantive(),confirm_evidence=True),**extra})
    def state(self,id):return next(r for r in self.sam.domain_chat.state()['implications'] if r['ref'].id==id)
    def test_new_criterion_and_requirement_challenge_pin_exact_existing_targets(self):
        for kind in ('challenge-requirement','new-criterion'):
            row=self.candidate(kind);self.assertEqual(row['body']['payload']['kind'],kind)
            self.assertEqual(row['body']['payload']['targets'],[pi.key(asdict(self.req['ref']))])
        ctx=self.sam.domain_chat.basis(self.current(self.sam,self.t),self.sam.domain_chat.plan(self.current(self.sam,self.t))[0],purpose='explore')[0]
        p=deepcopy(row['body']['payload']);p['targets']=[]
        p['kind']='challenge-requirement'
        with self.assertRaises(ValueError):pi.validate([p],ctx)
        p['kind']='new-criterion'
        p['targets']=[pi.key(asdict(self.req['ref']))];p['criterion']='Invented existing criterion'
        with self.assertRaises(ValueError):pi.validate([p],ctx)
        p['kind']='challenge-requirement';p['criterion']=self.req['body']['acceptance_criteria']
        pi.validate([p],ctx)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)
    def test_a_citation_and_model_claim_cannot_create_human_reviewed_readiness(self):
        row=self.candidate(support=self.substantive());state=self.state(row['ref'].id)['evidence_state']
        self.assertEqual(state['status'],'review-needed');self.assertFalse(state['ready_for_review']);self.assertFalse(state['human_reviewed'])
        with self.assertRaises(ValueError):self.review(row,confirm_evidence=False)
    def test_substantive_support_requires_citations_all_dimensions_and_no_material_gaps(self):
        support=self.substantive()
        with self.assertRaises(ValueError):pi.valid_support(support,[])
        support['gaps']=['Ownership authority is unknown.']
        with self.assertRaises(ValueError):pi.valid_support(support,[{}])
        support=self.substantive();support['corroboration']=''
        with self.assertRaises(ValueError):pi.valid_support(support,[{}])
    def test_review_is_versioned_exact_claim_bound_and_invalidated_by_changed_wording(self):
        row=self.candidate();saved=self.review(row);state=self.state(row['ref'].id)
        self.assertTrue(state['evidence_state']['ready_for_review']);self.assertEqual(state['evidence_state']['reviewed_by'],'sam')
        self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=saved['ref'],status='held',statement='A broader claim requiring different evidence.'))
        self.assertFalse(self.state(row['ref'].id)['evidence_state']['ready_for_review'])
        self.assertEqual(self.store.read(Ref(**saved['ref']),self.sam.scopes)['body']['evidence_review']['support'],self.substantive())
        with self.assertRaises(StaleBasis):self.review(row)
    def test_source_changes_prevent_confirming_the_old_assessment(self):
        row=self.candidate();source=self.draft(self.sam,self.t)['body']['source_refs'][0];old=self.store.read(Ref(**source),self.sam.scopes)
        self.store.put(source['id'],'source',old['scope'],{**old['body'],'text':'Revised observations.'},source['revision'])
        with self.assertRaises(StaleBasis):self.review(row)
        self.assertFalse(self.state(row['ref'].id)['evidence_state']['ready_for_review'])
    def test_another_domain_cannot_confirm_private_evidence(self):
        row=self.candidate()
        with self.assertRaises(PermissionError):self.lee.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held',evidence_review=self.substantive(),confirm_evidence=True))
    def test_legacy_cited_implications_remain_unassessed_not_silently_substantive(self):
        row=self.candidate();before=self.store.read(row['ref'],self.sam.scopes)
        self.assertEqual(self.state(row['ref'].id)['evidence_state']['status'],'unassessed')
        self.assertEqual(self.store.read(row['ref'],self.sam.scopes),before)
    def test_weak_evidence_can_be_shared_as_an_explicit_unresolved_proposal(self):
        row=self.candidate('new-criterion');support=self.substantive();support.update(assessment='limited',gaps=['Observe recovery on the actual prototype.'])
        held=self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=asdict(row['ref']),status='held',evidence_review=support,confirm_evidence=True))
        self.save(implication_refs=[held['ref']]);prepared=self.sam.command('domain-submission-prepare',{**self.data(),'include_evaluation':False})
        handoff=self.store.latest(prepared['domainHandoff'],self.sam.scopes)
        published=self.sam.command('domain-publish',dict(expected=handoff['body']['draft'],preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
        packet=self.store.resolve_packet(published['packet']['id'],published['packet']['revision'],{SCOPE})
        entry=next(e for r in packet['records'] if r['kind']=='contribution' for e in r['body']['working_report']['entries'] if e.get('project_implication'))
        self.assertIn('New acceptance criterion',entry['heading']);self.assertIn('Observe recovery',entry['text'])
        self.assertEqual(entry['project_implication']['status'],'limited');self.assertFalse(entry['project_implication']['ready_for_review'])
        self.assertEqual(entry['project_implication']['targets'],[pi.key(asdict(self.req['ref']))])
        self.assertTrue(entry['citations'][0]['ref']['id'].startswith('RELEASE-'))
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),self.req)

    def test_unassigned_new_criterion_remains_visible_but_cannot_be_ready_for_review(self):
        row=self.candidate('new-criterion');body=deepcopy(row['body']);body['payload']['targets']=[]
        body['evidence_review']=dict(support=self.substantive(),claim=pi.claim_signature(body['payload']),by='sam',at='2026-11-11')
        body['status']='held';state=pi.evidence_state({**row,'body':body},True)
        self.assertTrue(state['target_needed']);self.assertFalse(state['ready_for_review'])

    def test_selected_ai_passage_retains_origin_but_is_not_independent_evidence(self):
        self.send(self.sam,self.t);turn=next(t for t in self.sam.domain_chat.turns(self.current(self.sam,self.t)) if t['body']['role']=='assistant');quote=turn['body']['message'][:80]
        out=self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=None,status='held',kind='open-question',title='Captured idea',statement=quote,rationale='Investigate this idea with actual evidence.',selection=dict(turn=asdict(turn['ref']),text=quote)))
        row=self.store.read(Ref(**out['ref']),self.sam.scopes)
        self.assertEqual(row['body']['origin_selection']['turn'],asdict(turn['ref']));self.assertEqual(row['body']['payload']['evidence'],[])
        self.assertEqual(self.state(row['ref'].id)['evidence_state']['status'],'needs-evidence')
        with self.assertRaises(ValueError):self.sam.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=None,status='held',kind='open-question',title='Forged',statement='Forged',rationale='No evidence.',selection=dict(turn=asdict(turn['ref']),text='NOT IN THE SAVED REPLY')))
        with self.assertRaises(PermissionError):self.lee.command('domain-implication-save',dict(conversation=asdict(self.current(self.sam,self.t)['ref']),expected=None,status='held',kind='open-question',title='Forged',statement=quote,rationale='No evidence.',selection=dict(turn=asdict(turn['ref']),text=quote)))

    def test_new_criterion_cannot_use_a_goal_as_its_only_parent(self):
        ctx=self.sam.domain_chat.basis(self.current(self.sam,self.t),self.sam.domain_chat.plan(self.current(self.sam,self.t))[0],purpose='explore')[0]
        ctx['goals_and_measures']=[dict(kind='goal',ref=dict(id='GOAL-X',revision=1),body=dict(title='Outcome'))]
        p=self.model.implication(ctx);p.update(kind='new-criterion',targets=['GOAL-X:v1'],criterion='')
        with self.assertRaises(ValueError):pi.validate([p],ctx)
