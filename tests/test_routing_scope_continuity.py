"""Offline state/request-path tests; scripted responses are not semantic evaluation."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from workbench.core import Store, StaleBasis
from workbench.workspace import Workspace
from workbench.decisions import SCOPE
from workbench.intake import PRIVATE
from workbench.sponsor import QUESTIONS
from workbench import scope_context, integrity_grounding
from workbench.integrity import model_context
from workbench.integrity_example import Fixture
from test_intake import VALUE, CONTEXT
from test_integrity_meaning_basis import ContractModel


class NoModel:
    def status(self):return dict(configured=False, provider='offline', model='none')
    def generate(self, **kw):raise AssertionError('No live or scripted model call is needed here')


class SponsorScopeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'scope.sqlite3');self.addCleanup(self.store.close)
        self.w=Workspace(self.store,'priya',NoModel())
    def start(self):self.w.command('intake-start',dict(title='Synthetic scope continuity'))
    def ref(self):return asdict(self.w.intake.draft()['ref'])
    def save(self,answers):return self.w.command('sponsor-save',dict(expected=self.ref(),answers=answers))

    def test_new_draft_reuses_scope_and_unconfirmed_provenance_without_new_ratification(self):
        intent=self.store.put('INT-001','intent',SCOPE,dict(text='Existing purpose',status='ratified-for-investigation',
            execution='not-authorized',decision_id='INTDEC-old',intake=dict(out_scope='Emergency response',in_scope='Non-safety feedback',fallbacks='Central intake'),
            business_brief={'answers':{'q15':dict(items=['Emergency response'],roles=[],confirmed=False,ai=True,handled=True)}},
            sponsor_question_provenance={'q15':dict(status='sponsor-adopted-suggestion',citations=[dict(source_id='SOURCE-original',quote='Emergency response is excluded.')])}))
        decision=self.store.put('INTDEC-old','intent-decision',SCOPE,dict(intent=asdict(intent),actor='priya',
            disposition='publish-for-investigation',rationale='Enacted walkthrough, not actual stakeholder approval.'))
        self.store.depend(intent,decision,{SCOPE})
        before=self.store.read(intent,{SCOPE})
        self.start()
        state=self.w.sponsor.state()
        self.assertEqual(state['brief']['answers']['q15']['items'],['Emergency response'])
        self.assertFalse(state['brief']['answers']['q15']['confirmed'])
        self.assertEqual(self.w.intake.draft()['body']['values']['fallbacks'],'Central intake')
        self.assertEqual(self.store.read(intent,{SCOPE}),before)
        self.assertEqual(len(self.w.intake.state()['decisions']),1)

    def test_routing_edit_and_coach_preparation_preserve_scope_answer_and_specific_guidance(self):
        self.start();self.save({'q15':dict(items=['Emergency response is excluded.'],confirmed=True)})
        before=deepcopy(self.w.sponsor.state()['brief']['answers']['q15'])
        self.save({'q12':dict(items=['Unclear owner goes to central intake.'],confirmed=False)})
        with patch.object(self.w.coaching,'run',side_effect=lambda data,working_answer: self.w.coaching.prepare(data,test_answer=working_answer)):
            prepared=self.w.command('sponsor-coach',dict(expected=self.ref(),question='q12',consent=True))
        ctx=prepared['context']
        self.assertEqual(ctx['question_context']['answer_field'],'fallbacks')
        self.assertIn('path is known but not available',' '.join(ctx['question_context']['consider']))
        self.assertEqual(ctx['scope_context']['draft']['answers']['q15'],before)
        self.assertEqual(self.w.sponsor.state()['brief']['answers']['q15'],before)
        self.assertEqual(len(QUESTIONS),22)

    def test_native_publication_retains_question_provenance_and_exact_decision_link(self):
        self.start();i=self.w.intake
        i.save(dict(expected=self.ref(),step='value',**VALUE));i.accept_value(dict(expected=self.ref(),confirm=True))
        i.save(dict(expected=self.ref(),step='context',**CONTEXT))
        self.save({'q15':dict(items=['Emergency response is excluded.'],confirmed=False)})
        d=i.draft();d['body']['sponsor_question_provenance']={'q15':dict(status='sponsor-edited-suggestion',
            rationale='Source states a non-safety boundary.',citations=[dict(source_id='SOURCE-synthetic',quote='Non-safety feedback only.')])}
        i.save_draft(d,d['body']);i.build(dict(expected=self.ref()))
        p=self.w.command('intake-preflight',dict(expected=self.ref(),research_focus='Check boundaries',design_focus='Check routing'))
        case=self.w.command('intake-request',dict(expected=self.ref(),preflight=asdict(i.latest(p['id'])['ref']),confirm=True))
        for actor in ('sam','lee'):
            Workspace(self.store,actor,NoModel()).command('intake-review',dict(expected=asdict(i.latest(case['id'])['ref']),
                disposition='ready-for-investigation',rationale='Synthetic test only'))
        self.w.command('intake-publish',dict(expected=asdict(i.latest(case['id'])['ref']),confirm=True,rationale='Synthetic publication, not actual approval.'))
        intent=i.latest('INT-001');ctx=scope_context.for_coaching(i,i.draft())
        self.assertEqual(intent['body']['sponsor_question_provenance']['q15']['citations'][0]['source_id'],'SOURCE-synthetic')
        self.assertFalse(intent['body']['business_brief']['answers']['q15']['confirmed'])
        self.assertEqual(ctx['decisions'][0]['body']['intent'],asdict(intent['ref']))
        self.assertEqual(ctx['decisions'][0]['body']['disposition'],'publish-for-investigation')
        self.assertEqual(ctx['intents'][0]['body']['execution'],'not-authorized')

    def test_scope_change_invalidates_advice_without_losing_private_answer(self):
        self.start();self.save({'q12':dict(items=['Central intake'],confirmed=False)})
        d=self.w.intake.draft();saved=dict(scope_context=scope_context.for_coaching(self.w.intake,d))
        self.store.put('INT-001','intent',SCOPE,dict(intake={'out_scope':'Emergency response'},decision_id='INTDEC-missing'))
        with self.assertRaisesRegex(StaleBasis,'Scope decisions changed'):
            scope_context.require_coaching_basis(self.w.intake,d,saved)
        self.assertEqual(self.w.sponsor.state()['brief']['answers']['q12']['items'],['Central intake'])

    def test_new_policy_is_visible_without_silently_overwriting_saved_scope(self):
        self.start();self.save({'q15':dict(items=['Earlier declared exclusion'],confirmed=True)})
        draft=self.w.intake.draft();old=dict(scope_context=scope_context.for_coaching(self.w.intake,draft))
        policy=self.store.put('POL-001','policy',SCOPE,dict(text='A separately recorded policy boundary',status='user-declared-boundary'))
        current=scope_context.for_coaching(self.w.intake,draft)
        self.assertEqual(current['policies'][0]['ref'],asdict(policy))
        self.assertEqual(current['draft']['values']['out_scope'],'Earlier declared exclusion')
        with self.assertRaises(StaleBasis):scope_context.require_coaching_basis(self.w.intake,draft,old)


class IntegrityScopeTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close);s=self.f.store
        self.intent=s.put('INT-scope','intent',SCOPE,dict(text='Synthetic purpose',intake={'out_scope':'Emergency response'},
            status='ratified-for-investigation',execution='not-authorized',decision_id='INTDEC-scope',
            scaffold=[{'unrelated':'x'*100_000}],business_brief={'answers':{'q15':dict(items=['Emergency response'],confirmed=False)}},
            sponsor_question_provenance={'q15':dict(citations=[dict(source_id='SOURCE-private-not-fetched',quote='Emergency is excluded.')])}))
        self.decision=s.put('INTDEC-scope','intent-decision',SCOPE,dict(intent=asdict(self.intent),actor='priya',
            authority={'role':'sponsor'},disposition='publish-for-investigation',rationale='Enacted synthetic walkthrough, not actual stakeholder approval.',
            boundary='Investigation only; delivery not authorized.'))
        for r in (self.intent,self.decision):s.depend(self.f.anchor,r,{SCOPE})
        s.depend(self.intent,self.decision,{SCOPE})
        self.w=self.f.w('sam',NoModel());self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory')

    def test_both_model_projections_carry_exact_scope_without_promoting_it_to_packet_evidence(self):
        before=self.f.store.read(self.intent,{SCOPE})
        ctx=self.w.integrity.assemble(self.data)
        mapping=integrity_grounding.project(ctx,integrity_grounding.batches(ctx)[0]);joint=model_context(ctx)
        for request in (mapping,joint):
            scope=request['scope_context']
            self.assertEqual(scope['intents'][0]['ref'],asdict(self.intent))
            self.assertEqual(scope['intents'][0]['body']['intake']['out_scope'],'Emergency response')
            self.assertIn('not actual stakeholder approval',scope['decisions'][0]['body']['rationale'])
            self.assertEqual(scope['missing_decisions'],[])
            self.assertNotIn(self.intent.id,{c['id'] for c in request['packet_evidence'].values()})
            self.assertNotIn(self.decision.id,{c['id'] for c in request['packet_evidence'].values()})
        self.assertEqual(self.f.store.read(self.intent,{SCOPE}),before)
        self.assertNotIn('scaffold',joint['scope_context']['intents'][0]['body'])

    def test_historical_selection_does_not_replace_old_scope_with_latest_scope(self):
        old=self.f.store.read(self.intent,{SCOPE})
        self.f.store.put(self.intent.id,'intent',SCOPE,{**old['body'],'intake':{'out_scope':'A newer different boundary'}},1)
        data={**self.data,'review_purpose':'historical','historical_reason':'Compare exact earlier scope and evidence.'}
        ctx=self.w.integrity.assemble(data)
        self.assertEqual(model_context(ctx)['scope_context']['intents'][0]['body']['intake']['out_scope'],'Emergency response')
        with self.assertRaisesRegex(StaleBasis,'superseded'):
            self.w.command('integrity-assess',{**self.data,'semantic':True,'consent':True})

    def test_explicit_omission_is_visible_and_does_not_silently_restore_or_invent_decision(self):
        data={**self.data,'comparison_excluded_dependencies':[dict(ref=asdict(self.decision),reason='Deliberate offline omission test.')]}
        ctx=self.w.integrity.assemble(data);scope=model_context(ctx)['scope_context']
        self.assertEqual(scope['decisions'],[])
        self.assertEqual(scope['missing_decisions'][0]['decision_id'],self.decision.id)
        self.assertEqual(scope['omitted_dependencies'][0]['ref'],asdict(self.decision))

    def test_native_mapping_joint_save_and_reuse_keep_the_same_scope_context(self):
        model=ContractModel();w=self.f.w('sam',model)
        refs=[asdict(self.f.anchor)];body=self.f.store.read(self.f.anchor,{SCOPE})['body']
        for n in range(2):refs.append(asdict(self.f.store.put('COPY-'+str(n),'requirement',SCOPE,deepcopy(body))))
        expression=self.f.review(self.f.a['ref'])['body']
        revised=w.integrity.expression(dict(source=expression['source'],domain='research',label='Scheduling',requirements=refs,
            facts=expression['facts'],expected=self.f.a['ref']))
        data={**self.data,'packets':[revised['packet']],'semantic':True,'consent':True}
        result=w.command('integrity-assess',data)
        calls=[c for c in model.calls if c['context'].get('assessment_phase') in ('clause-mapping','joint-comparison')]
        self.assertTrue(any(c['context']['assessment_phase']=='joint-comparison' for c in calls))
        for call in calls:
            self.assertEqual(call['context']['scope_context']['intents'][0]['ref'],asdict(self.intent))
            self.assertIn(scope_context.INSTRUCTIONS,call['instructions'])
        saved=self.f.review(result['ref'])['body'];self.assertEqual(saved['approval'],'not-granted')
        self.assertEqual(model_context(saved['context'])['scope_context'],calls[-1]['context']['scope_context'])
        count=len(model.calls);self.assertTrue(w.command('integrity-assess',data)['cached']);self.assertEqual(len(model.calls),count)
