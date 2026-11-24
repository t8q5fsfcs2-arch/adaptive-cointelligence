"""Synthetic SQLite proof: situated meaning, audience and exact decision basis."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from workbench.core import Ref, Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.need_contexts import DIMENSIONS, KIND
import test_bridge as bridge_fixtures


class NeedContextTests(unittest.TestCase):
    def setUp(self):
        self.fixture=bridge_fixtures.BridgeTests();self.fixture.setUp()
        self.store=self.fixture.store
        self.w=self.fixture.w
        self.research=self.fixture.research
        self.req=self.fixture.req
        self.rc=self.fixture.rc
        self.shared_source=self.store.read(Ref(**self.rc['body']['source_refs'][0]),{SCOPE})
    def tearDown(self):self.fixture.tearDown()
    def payload(self):
        e=asdict(self.shared_source['ref'])
        return dict(title='Resuming a paused task',claim='A progress cue may help this participant resume after a pause.',
            rationale='Keep the actor, task and evidence together.',limitation='One fictional session; no measured prevalence or business benefit.',
            confirm_shared=True,evidence=[dict(ref=e,quote='A fictional participant resumed after a pause.',use='active',rationale='Observed fictional resumption.')],
            dimensions={k:dict(text={'people':'One fictional participant','job':'Resume a paused task','situation':'Returning after a pause','triggers':'The interruption ends','pains':'Where to resume is unclear','gains':'Continue without repeating work','boundaries':'One fictional task only','dependencies':'Resumption may depend on a visible progress cue; this is unvalidated.'}[k],
                               state='interpretation',evidence_ids=['E1']) for k in DIMENSIONS},
            links=[dict(ref=asdict(self.req['ref']),relation='refines',rationale='Make resumption observable.',conditions='During the scoped task after a pause.',use='active'),
                   dict(ref=asdict(self.rc['ref']),relation='supports',rationale='This published finding supplied the interpretation.',conditions='One fictional session only.',use='historical')])
    def save(self,p=None):
        result=self.w('sam').command('need-context-save',p or self.payload())
        return self.store.read(Ref(**result['ref']),{SCOPE})
    def packet(self,r):
        return self.w('sam').command('need-context-packet',dict(expected=asdict(r['ref']),purpose='Synthetic situated context review'))['packet']
    def issue(self,r):
        p=self.fixture.payload();p['packet_refs'].append(self.packet(r))
        result=self.w('sam').command('bridge-raise',p)
        return self.store.latest(result['id'],{SCOPE})

    def test_one_identity_reused_in_research_design_packets_and_pending_review(self):
        before=self.store.latest(self.req['ref'].id,{SCOPE});r=self.save()
        for actor,draft in [('sam',self.research[2]),('lee',self.fixture.design[2])]:
            ctx=self.w(actor).domains.context(asdict(draft['ref']))
            self.assertEqual(ctx['user_needs_and_situations'][0]['ref'],asdict(r['ref']))
            self.assertIn(asdict(r['ref']),ctx['basis'])
        result=self.w('sam').command('domain-prepare',dict(expected=asdict(self.research[2]['ref']),recipient='design',intent_implications='Investigate the cue',downstream_needs='Test resumption',open_questions='Which cue?'))
        handoff=self.store.latest(result['domainHandoff'],self.w('sam').scopes)
        packet=self.store.resolve_packet(**handoff['body']['packet'],allowed_scopes=self.w('sam').scopes)
        self.assertIn(r['ref'],[x['ref'] for x in packet['records']])
        i=self.issue(r);self.fixture.propose(i);case=self.fixture.case(i)
        self.assertIn(asdict(r['ref']),case['body']['basis'])
        self.assertEqual(case['body']['status'],'pending-review')
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE}),before)
        self.assertEqual(self.w('alex').loop.history(),[])

    def test_historical_intent_and_revisions_reconstruct_without_becoming_active_approval_basis(self):
        old=self.store.latest('INT-001',{SCOPE});new=self.store.put('INT-001','intent',SCOPE,{**old['body'],'text':'Changed direction'},old['ref'].revision)
        p=self.payload();p['links'] += [dict(ref=asdict(old['ref']),relation='challenges',rationale='Earlier starting hypothesis.',conditions='Historical comparison only.',use='historical'),dict(ref=asdict(new),relation='refines',rationale='Current direction.',conditions='Scoped revised direction.',use='active')]
        r=self.save(p);raw=self.packet(r)
        p['expected']=asdict(r['ref']);p['claim']='Further clarify the resumption interpretation.'
        newer=self.save(p)
        resolved=self.store.resolve_packet(**raw,allowed_scopes={SCOPE})
        original=next(x for x in resolved['records'] if x['kind']==KIND)
        self.assertEqual(original,r)
        self.assertIn(old['ref'],[x['ref'] for x in resolved['records']]);self.assertIn(new,[x['ref'] for x in resolved['records']])
        self.assertIn(dict(previous=asdict(r['ref']),current=asdict(newer['ref'])),resolved['changed_refs'])
        basis=self.w('alex').need_contexts.selected_basis([asdict(newer['ref'])])
        self.assertIn(new,basis);self.assertNotIn(old['ref'],basis)
        self.store.close();self.store=Store(self.fixture.fixture.path);self.fixture.store=self.store;self.fixture.fixture.store=self.store
        self.assertEqual(self.store.read(r['ref'],{SCOPE}),r)

    def test_private_or_unverifiable_evidence_and_unsupported_details_fail_atomically(self):
        before=self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        for change,error in [('private',PermissionError),('invented',ValueError),('no-basis',ValueError),('no-consent',ValueError)]:
            p=self.payload()
            if change=='private':p['evidence'][0]['ref']=asdict(self.research[1]['ref'])
            if change=='invented':p['evidence'][0]['quote']='Nobody ever said this.'
            if change=='no-basis':p['dimensions']['pains'].update(state='source-stated',evidence_ids=[])
            if change=='no-consent':p['confirm_shared']=False
            with self.subTest(change=change),self.assertRaises(error):self.save(p)
            self.assertEqual(before,self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0])

    def test_author_rights_and_stale_edit_protect_existing_context(self):
        r=self.save();p={**self.payload(),'expected':asdict(r['ref'])}
        for actor in ['lee','alex']:
            with self.subTest(actor=actor),self.assertRaises(PermissionError):self.w(actor).command('need-context-save',p)
        self.save(p)
        with self.assertRaises(StaleBasis):self.save(p)
        self.assertEqual(self.store.read(r['ref'],{SCOPE}),r)

    def test_changed_context_blocks_stale_review_and_keeps_prior_packet(self):
        r=self.save();raw=self.packet(r);i=self.issue(r);self.fixture.propose(i)
        self.fixture.reviews(i)
        self.save({**self.payload(),'expected':asdict(r['ref']),'claim':'A revised, still provisional interpretation.'})
        with self.assertRaises(StaleBasis):self.fixture.decide(i)
        self.assertEqual(self.store.latest(self.req['ref'].id,{SCOPE})['ref'],self.req['ref'])
        self.assertEqual(next(x for x in self.store.resolve_packet(**raw,allowed_scopes={SCOPE})['records'] if x['kind']==KIND),r)

    def test_active_evidence_change_blocks_preflight_and_new_commitment_basis(self):
        r=self.save();src=self.shared_source
        self.store.put(src['ref'].id,src['kind'],SCOPE,{**src['body'],'text':'Revised evidence'},src['ref'].revision)
        with self.assertRaises(StaleBasis):self.w('alex').need_contexts.selected_basis([asdict(r['ref'])])
        with self.assertRaises(StaleBasis):self.w('sam').command('domain-prepare',dict(expected=asdict(self.research[2]['ref']),recipient='design',intent_implications='Review changed evidence',downstream_needs='Wait',open_questions='What changed?'))

    def test_authorized_synthetic_decision_retains_context_and_later_change_flags_requirement(self):
        r=self.save();i=self.issue(r);self.fixture.propose(i);self.fixture.reviews(i);self.fixture.decide(i)
        changed=self.store.latest(self.req['ref'].id,{SCOPE})
        self.assertIn(r['ref'],list(self.store.graph({SCOPE}).successors(changed['ref'])))
        p={**self.payload(),'expected':asdict(r['ref']),'claim':'Reconsider the cue after new evidence.'}
        # Update the target reference rather than treating its accepted successor as interchangeable.
        p['links'][0]['ref']=asdict(changed['ref'])
        self.save(p)
        self.assertTrue(self.w('alex').state()['requirement_impacts'][changed['ref'].id])
        self.assertEqual(self.store.latest(changed['ref'].id,{SCOPE})['ref'],changed['ref'])

    def test_selection_is_relevant_and_saved_design_plan_is_not_silently_rewritten(self):
        plans=self.w('lee').domain_brief.state();self.assertTrue(plans)
        old=self.store.read(plans[0]['ref'],self.w('lee').scopes)
        r=self.save();service=self.w('lee').need_contexts
        self.assertEqual(service.related([Ref('UNRELATED',1)]),[])
        plan=self.w('lee').domain_brief.state()[0]
        self.assertEqual(plan['situated_context']['to_review'],[asdict(r['ref'])])
        self.assertEqual(plan['situated_context']['included'],[])
        self.assertFalse(plan['current'])
        self.assertEqual(self.store.read(old['ref'],self.w('lee').scopes),old)
        ctx=self.w('lee').domain_brief.context(include_brief=True)
        self.assertEqual(ctx['user_needs_and_situations'][0]['ref'],asdict(r['ref']))

    def test_brief_uses_selected_passages_not_whole_sources_and_supplies_requirement_wording_once(self):
        source=self.shared_source
        updated=self.store.put(source['ref'].id,source['kind'],SCOPE,{**source['body'],'text':source['body']['text']+' Irrelevant confidential-looking filler.'*20000},source['ref'].revision)
        self.shared_source=self.store.read(updated,{SCOPE});r=self.save()
        ctx=self.w('lee').domain_brief.context(include_brief=True)
        projected=next(v for v in ctx['evidence_records'] if v['ref']==asdict(updated))
        self.assertEqual(projected['body']['selected_passages'],['A fictional participant resumed after a pause.'])
        self.assertNotIn('Irrelevant confidential-looking filler',str(ctx))
        self.assertIn(asdict(updated),ctx['basis'])
        full_req=next(v for v in ctx['requirements'] if v['ref']==asdict(self.req['ref']))
        self.assertEqual(full_req['body']['text'],self.req['body']['text'])
        duplicate=next(v for v in ctx['evidence_records'] if v['ref']==asdict(self.req['ref']))
        self.assertNotIn('text',duplicate['body'])
        self.assertEqual(self.store.read(updated,{SCOPE}),self.shared_source)

    def change_payload(self,previous):
        p={**self.payload(),'expected':asdict(previous['ref']),'claim':'Accepted ownership needs a current responsible shift and next action.',
           'change_summary':'A fictional follow-up qualifies the earlier acceptance hypothesis.', 'example':'fictional-follow-up'}
        public=self.fixture.dc['body']['design_brief']
        p['review_items']=[
            dict(target=asdict(self.req['ref']),field='text',proposed_text='Preserve continuing responsibility through shift change.',rationale='Acceptance alone may become ambiguous.',evidence_ids=['E1']),
            dict(target=asdict(self.req['ref']),field='acceptance_criteria',proposed_text='Observe an accepted task during shift change without assuming reassignment.',rationale='Test continuity separately from initial acceptance.',evidence_ids=['E1']),
            dict(target=public,field='objectives',proposed_text='Compare two shift-handoff views in human research.',rationale='The plan needs another testable question.',evidence_ids=['E1'])]
        return p

    def test_new_packet_revision_keeps_exact_earlier_meaning_and_proposed_target_comparison(self):
        r=self.save();packet=self.packet(r);before=self.store.resolve_packet(**packet,allowed_scopes={SCOPE})
        requirement=self.store.latest(self.req['ref'].id,{SCOPE});brief=self.store.read(Ref(**self.fixture.dc['body']['design_brief']),{SCOPE})
        updated=self.save(self.change_payload(r));result=self.w('sam').command('need-context-packet',dict(expected=asdict(updated['ref']),purpose='Updated context review',previous_packet=packet))['packet']
        self.assertEqual(result,dict(id=packet['id'],revision=2))
        self.assertEqual(self.store.read_packet(**packet,allowed_scopes={SCOPE})['refs'],before['refs'])
        old=self.store.resolve_packet(**packet,allowed_scopes={SCOPE});self.assertEqual(old['records'],before['records'])
        newer=self.store.resolve_packet(**result,allowed_scopes={SCOPE});self.assertIn(r['ref'],[v['ref'] for v in newer['records']]);self.assertIn(updated['ref'],[v['ref'] for v in newer['records']])
        self.assertEqual(updated['body']['review_items'][0]['current_text'],requirement['body']['text'])
        self.assertEqual({i['status'] for i in updated['body']['review_items']},{'reconsideration-needed'})
        self.assertEqual(self.store.latest(requirement['ref'].id,{SCOPE}),requirement);self.assertEqual(self.store.latest(brief['ref'].id,{SCOPE}),brief)
        self.assertIn('claim',updated['body']['changed_fields'])
        plan=self.w('lee').domain_brief.state()[0];self.assertIn(asdict(updated['ref']),plan['situated_context']['to_review'])
        ctx=self.w('lee').domain_brief.context(include_brief=True)
        self.assertNotIn(asdict(brief['ref']),ctx['basis']);self.assertEqual(updated['body']['review_items'][-1]['target'],asdict(brief['ref']))

    def test_packet_revision_authority_identity_and_optimistic_concurrency_are_enforced(self):
        r=self.save();packet=self.packet(r);updated=self.save(self.change_payload(r))
        other=self.save({**self.payload(),'title':'Another situation'})
        with self.assertRaises(PermissionError):self.w('lee').command('need-context-packet',dict(expected=asdict(updated['ref']),purpose='Wrong author',previous_packet=packet))
        with self.assertRaises(PermissionError):self.w('sam').command('need-context-packet',dict(expected=asdict(other['ref']),purpose='Wrong identity',previous_packet=packet))
        self.w('sam').command('need-context-packet',dict(expected=asdict(updated['ref']),purpose='Current context',previous_packet=packet))
        third=self.save({**self.change_payload(updated),'claim':'Another explicit revision.'})
        with self.assertRaises(StaleBasis):self.w('sam').command('need-context-packet',dict(expected=asdict(third['ref']),purpose='Stale manifest',previous_packet=packet))
        self.assertEqual(self.store.db.execute('SELECT MAX(revision) FROM packets WHERE id=?',(packet['id'],)).fetchone()[0],2)

    def test_review_targets_require_shared_current_records_and_active_evidence(self):
        r=self.save();p=self.change_payload(r);count=self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]
        p['review_items'][0]['target']=asdict(self.research[2]['ref'])
        with self.assertRaises(PermissionError):self.save(p)
        p=self.change_payload(r);p['review_items'][0]['evidence_ids']=['INVENTED']
        with self.assertRaises(ValueError):self.save(p)
        p=self.change_payload(r);p['review_items'][0]['field']='status'
        with self.assertRaises(ValueError):self.save(p)
        p=self.change_payload(r);p['review_items'].append(deepcopy(p['review_items'][0]))
        with self.assertRaises(ValueError):self.save(p)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0],count)

    def test_editing_a_reconsideration_target_does_not_create_a_self_invalidating_context_cycle(self):
        old=self.save();updated=self.save(self.change_payload(old));target=Ref(**self.fixture.dc['body']['design_brief']);brief=self.store.read(target,{SCOPE})
        self.store.put(target.id,brief['kind'],SCOPE,{**brief['body'],'objectives':[{'title':'Revised by its domain'}]},target.revision)
        basis=self.w('lee').need_contexts.selected_basis([asdict(updated['ref'])])
        self.assertIn(updated['ref'],basis);self.assertNotIn(target,basis)
        packet=self.w('sam').command('need-context-packet',dict(expected=asdict(updated['ref']),purpose='Compare the original target without making it active evidence'))['packet']
        selected=self.store.resolve_packet(**packet,allowed_scopes={SCOPE})
        self.assertIn(target,[r['ref'] for r in selected['records']])
        self.assertEqual(self.store.read(updated['ref'],{SCOPE})['body']['review_items'][-1]['target'],asdict(target))
