"""Native-path contract checks with explicit synthetic outputs; no semantic claim."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from unittest.mock import patch
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench import integrity_options as options, integrity_parts as parts
from workbench import integrity_interpretation as meaning
from workbench.integrity import model_context
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.core import Ref, StaleBasis


def unresolved(state='conditional'):
    return dict(state=state,reading='The synthetic condition concerns the active state.',
        basis='The source wording permits two materially different readings for this use.',
        alternatives=[dict(reading='It concerns recoverable history only.',consequence='Historical retrieval would not establish the active-state invariant.')],
        clarification=dict(question='Must active state remain unchanged, or is recoverable history sufficient?',
            owner_role='Requirement owner',dependent_action='Accept the active-state behavior as supported.',
            release_condition='Record the authorized scope answer and reassess the corresponding source evidence.'))


class ContractModel:
    """Scripted responses exercise the actual pipeline, never stand in for a model eval."""
    def __init__(self):self.calls=[];self.before_grade=None
    def status(self):return dict(configured=True,provider='scripted',model='meaning-contract-test')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));ctx=kw['context'];phase=ctx.get('assessment_phase')
        out=synthetic_output(ctx,phase='investigate')
        if phase not in ('condition-inventory','condition-inventory-review'):
            if self.before_grade:self.before_grade()
            for n,finding in enumerate(out['decision']['packet_findings']):
                for part in finding['parts']:part['interpretation']=unresolved('conditional' if n%2 else 'clarification-required')
                finding.update(parts.parent(finding['parts'],ctx['option_contract']['material_parts']))
            if phase=='clause-mapping':
                out={k:out['decision'][k] for k in ('obligations','packet_findings')}
                out['applicability']={key:dict(status='shared',rationale='Synthetic identical copied clauses have shared applicability.',
                    occurrences={o['clause_ref']:dict(status='same-meaning',rationale='The synthetic original occurrences have identical qualifiers.') for o in target['occurrences']}) for key,target in ctx['governing_targets'].items()}
            elif phase=='joint-comparison':
                for key in ('obligations','packet_findings'):out['decision'].pop(key)
        return dict(output=out,model='scripted',usage={})


class MeaningBasisTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close);self.model=ContractModel();self.w=self.f.w('sam',self.model)
        self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True)

    def assess(self):return self.w.command('integrity-assess',self.data)
    def history(self):self.data.update(review_purpose='historical',historical_reason='Compare the original selected evidence against the frozen conditions.')
    def change_source(self):
        r=self.f.store.latest('SOURCE-sam',{SCOPE})
        return self.f.store.put(r['ref'].id,r['kind'],r['scope'],{**r['body'],'text':'Changed synthetic evidence.'},r['ref'].revision)

    def test_no_missing_disposition_placeholder_or_unresolved_supported_judgment(self):
        ctx=self.w.integrity.assemble(self.data);out=synthetic_output(model_context(ctx))['decision']
        for mutation in (lambda p:p.pop('interpretation'),
                         lambda p:p['interpretation'].update(basis='TBD'),
                         lambda p:p.update(interpretation=unresolved()),
                         lambda p:p['interpretation'].update(alternatives=unresolved()['alternatives'])):
            bad=deepcopy(out);mutation(bad['packet_findings'][0]['parts'][0])
            with self.assertRaises(ValueError):options.validate(self.w.integrity,bad,ctx,[])

    def test_unresolved_meaning_requires_complete_question_and_action_boundary(self):
        ctx=self.w.integrity.assemble(self.data);out=synthetic_output(model_context(ctx),phase='investigate')['decision']
        for mutation in (lambda m:m.update(alternatives=[]),lambda m:m.update(clarification=None),
                         lambda m:m['clarification'].update(owner_role='unknown'),
                         lambda m:m['clarification'].update(release_condition='pending')):
            bad=deepcopy(out);p=bad['packet_findings'][0]['parts'][0];p['interpretation']=unresolved();mutation(p['interpretation'])
            with self.assertRaises(ValueError):options.validate(self.w.integrity,bad,ctx,[])

    def test_evidence_gap_does_not_manufacture_language_ambiguity(self):
        ctx=self.w.integrity.assemble(self.data);out=synthetic_output(model_context(ctx),phase='investigate')['decision']
        saved,_=options.validate(self.w.integrity,out,ctx,[])
        self.assertTrue(saved['recommendation']['unresolved_material_gaps'])
        self.assertEqual(saved['recommendation']['unresolved_interpretations'],[])
        self.assertEqual(saved['recommendation']['preferred_option'],'C')

    def assert_carried(self,record):
        trace=record['decision_trace'];items=trace['recommendation']['unresolved_interpretations']
        all_parts=[p for f in trace['packet_findings'] for p in f['parts']]
        self.assertEqual(len(items),len(all_parts))
        for item in items:
            self.assertIn(item['text'],record['summary'])
            self.assertIn(item['text'],trace['recommendation']['conditions'])
            self.assertIn(item['text'],trace['recommendation']['would_change_if'])
            self.assertIn('no human answer',item['authority'])
        self.assertEqual(record['approval'],'not-granted')
        self.assertEqual(trace['recommendation']['preferred_option'],'C')
        self.assertTrue(all(p['status']=='uncertain' for p in all_parts))
        self.assertTrue(all(p['evidence_quotes'] for p in all_parts))

    def test_actual_single_request_saves_all_meaning_decisions_and_all_evidence_gaps(self):
        result=self.assess();self.assert_carried(self.w.command('integrity-review-read',dict(assessment=result['ref'])))
        self.assertIn(meaning.INSTRUCTIONS,self.model.calls[-1]['instructions'])
        count=len(self.model.calls);again=self.assess()
        self.assertTrue(again['cached']);self.assertEqual(count,len(self.model.calls))

    def test_actual_bounded_mapping_carries_dispositions_into_joint_and_saved_recommendation(self):
        refs=[asdict(self.f.anchor)];body=self.f.store.read(self.f.anchor,{SCOPE})['body']
        for n in range(2):refs.append(asdict(self.f.store.put('COPY-'+str(n),'requirement',SCOPE,deepcopy(body))))
        expression=self.f.review(self.f.a['ref'])['body']
        revised=self.w.integrity.expression(dict(source=expression['source'],domain='research',label='Scheduling',
            requirements=refs,facts=expression['facts'],expected=self.f.a['ref']))
        self.data['packets']=[revised['packet']]
        result=self.assess();record=self.w.command('integrity-review-read',dict(assessment=result['ref']))
        self.assert_carried(record)
        mappings=[call for call in self.model.calls if call['context'].get('assessment_phase')=='clause-mapping']
        joint=next(call for call in self.model.calls if call['context'].get('assessment_phase')=='joint-comparison')
        self.assertTrue(mappings)
        self.assertEqual(joint['context']['unresolved_interpretations'],meaning.unresolved(record['decision_trace']['packet_findings']))
        self.assertTrue(all(meaning.INSTRUCTIONS in call['instructions'] for call in mappings))

    def test_current_superseded_dependency_stops_before_inventory_or_grading(self):
        self.change_source();before=self.f.store.db.total_changes
        preview=self.w.command('integrity-preflight',self.data)
        self.assertFalse(preview['current_use_eligible'])
        self.assertEqual(preview['superseded'][0]['selected'],dict(id='SOURCE-sam',revision=1))
        for action in ('integrity-assess','integrity-inventory-prepare'):
            with self.assertRaisesRegex(StaleBasis,'superseded'):self.w.command(action,self.data)
        self.assertEqual(self.model.calls,[]);self.assertEqual(self.f.store.db.total_changes,before)

    def test_historical_reason_required_and_formal_historical_rejected(self):
        for changes in (dict(review_purpose='historical'),dict(review_purpose='historical',historical_reason='TBD'),
                        dict(review_purpose='historical',historical_reason='Preserve the comparison.',mode='formal',confirm=True)):
            with self.assertRaises(ValueError):self.w.command('integrity-assess',{**self.data,**changes})
        self.assertEqual(self.model.calls,[])

    def test_historical_exact_versions_reused_after_newer_source_and_packet(self):
        self.history();first=self.assess();count=len(self.model.calls);new=self.change_source()
        self.f.expression('sam','research','Scheduling','Changed synthetic evidence.',['assignment'],previous=self.f.a['ref'],source=new)
        again=self.assess();self.assertTrue(again['cached']);self.assertEqual(again['ref'],first['ref'])
        self.assertTrue(again['summary'].startswith('Historical comparison only.'))
        self.assertEqual(len(self.model.calls),count)
        self.assertFalse(again['review_basis']['current_use_eligible'])
        self.assertGreaterEqual(len(again['review_basis']['superseded']),2)
        saved=self.w.command('integrity-review-read',dict(assessment=first['ref']))
        self.assertTrue(saved['stale']);self.assertEqual(saved['context']['packets'],self.data['packets'])

    def test_historical_can_review_superseded_governing_requirement_without_refresh(self):
        original=self.f.store.read(self.f.anchor,{SCOPE});self.f.store.put(self.f.anchor.id,'requirement',SCOPE,{**original['body'],'text':'New governing scope.'},1)
        self.history();result=self.assess();saved=self.f.review(result['ref'])['body']
        self.assertEqual(saved['context']['requirements'],[asdict(self.f.anchor)])
        self.assertEqual(saved['context']['condition_inventory']['evidence_level'],'documentary-alignment')
        self.assertFalse(result['review_basis']['current_use_eligible'])

    def test_historical_review_cannot_be_approved(self):
        self.history();result=self.assess()
        with self.assertRaises(DecisionBlocked):self.w.command('integrity-approve-domain',dict(assessment=result['ref'],disposition='approved-with-limits',rationale='Keep the limits.'))
        self.assertTrue(self.w.integrity.freshness(self.f.review(result['ref'])))
        self.assertFalse(self.w.integrity.freshness(self.f.review(result['ref']),for_current_use=False))

    def test_historical_review_cannot_be_attached_to_current_issue(self):
        current=self.f.assessment()['ref'];issue=self.f.issue(current)
        self.history();self.data.update(packets=[self.f.a['packet'],self.f.b['packet']],evaluation_scope='cross-domain')
        history=self.assess()
        with self.assertRaises(DecisionBlocked):self.f.w('alex').command('integrity-attach',dict(expected=asdict(self.f.current(issue)['ref']),assessment=history['ref']))

    def test_historical_cache_is_invalidated_by_method_or_current_authority(self):
        self.history();first=self.assess();saved=self.f.review(first['ref'])
        import workbench.integrity as service
        with patch.object(service,'PROMPT_VERSION','changed-method'):
            self.assertTrue(self.w.integrity.freshness(saved,for_current_use=False))
        rights=self.w.rights.snapshot('requirement');rights['decider']='lee'
        with patch.object(self.w.rights,'snapshot',return_value=rights):
            self.assertTrue(self.w.integrity.freshness(saved,for_current_use=False))

    def test_current_saved_review_invalidates_before_new_call_when_dependency_changes(self):
        self.assess();count=len(self.model.calls);self.change_source()
        with self.assertRaises(StaleBasis):self.assess()
        self.assertEqual(len(self.model.calls),count)

    def test_inflight_current_change_rejects_assessment_save(self):
        self.model.before_grade=self.change_source
        with self.assertRaises(StaleBasis):self.assess()
        self.assertFalse(self.w.integrity.records('integrity-assessment'))

    def test_historical_reuse_does_not_bypass_access(self):
        self.history();self.assess();count=len(self.model.calls);original=self.f.store.read
        def read(ref,scopes):
            if ref.id=='SOURCE-sam':raise PermissionError('Revoked access')
            return original(ref,scopes)
        with patch.object(self.f.store,'read',side_effect=read):
            with self.assertRaises((PermissionError,StaleBasis)):self.assess()
        self.assertEqual(len(self.model.calls),count)

    def test_historical_and_current_never_share_assessment_cache_entry(self):
        current=self.assess();self.history();historical=self.assess()
        self.assertNotEqual(current['ref'],historical['ref'])
        self.assertFalse(historical['cached'])

    def test_current_source_versions_do_not_make_an_obsolete_method_eligible(self):
        result=self.assess()
        import workbench.integrity as service
        with patch.object(service,'PROMPT_VERSION','changed-method'):
            view=self.w.command('integrity-review-read',dict(assessment=result['ref']))
        self.assertTrue(view['review_basis_now']['selected_versions_current'])
        self.assertFalse(view['review_basis_now']['current_use_eligible'])
        self.assertTrue(view['review_basis_now']['current_use_blockers'])
