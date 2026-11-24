"""Offline fault injection for selective reconsideration, not semantic validation."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from unittest.mock import patch
import test_integrity_condition_batches as batching
from workbench import integrity_corrections as corrections, integrity_options as options
from workbench.core import StaleBasis
from workbench.decisions import DecisionBlocked


class CorrectionModel(batching.WindowModel):
    def __init__(self):
        super().__init__();self.disposition='revise';self.fault=None;self.fail_batch=None;self.corrections=0
    def generate(self,**kw):
        if kw['context'].get('assessment_phase')!='targeted-correction':return super().generate(**kw)
        self.calls.append(deepcopy(kw));self.corrections+=1
        if self.corrections==self.fail_batch:raise RuntimeError('Synthetic interrupted batch')
        out={}
        for key,t in kw['context']['correction_targets'].items():
            v=dict(disposition=self.disposition,rationale='The quoted synthetic evidence does not establish the required event relationship.',replacement=None,follow_up=None,clarification=None)
            if self.disposition=='revise':
                if t['mode']=='follow-up':v['follow_up']='Who owns recording event C10, and what record can verify that it occurred?'
                else:
                    p=deepcopy(t['previous'])
                    for k in ('part_ref','claim_interpretation','support_scope','evidence_refs'):p.pop(k)
                    p.update(status='absent',evidence_quotes=[],reasoning='No inspected synthetic assertion establishes this particular event.',remaining_gap='Provide the event record and its responsible owner.')
                    p['evidence_relationship'].update(relation='no-assertion',source_assertion='The inspected source contains no assertion about this particular event.',missing_link='This event record and its responsible owner are unestablished.',evidence_request='Provide the event record and its responsible owner.')
                    p['entailment_check']=dict(counterexample_possible=True,explanation='The generic event record may omit this required event.')
                    v['replacement']=p
            elif self.disposition=='clarification-required':
                v['clarification']=dict(question='Does this event name mean dispatch or completion?',owner_role='Requirement owner',dependent_action='Endorse this event judgment',release_condition='An authorized interpretation distinguishes dispatch from completion.')
            out[key]=v
        options.shape(out,kw['schema'])
        if self.fault:self.fault(out,kw['context'])
        return dict(output=out,model='scripted',response_id='correction-fixture-'+str(self.corrections),usage=dict(input_tokens=100,output_tokens=10,total_tokens=110))


class TargetedCorrectionTests(unittest.TestCase):
    def setUp(self):
        batching.ConditionBatchTests.setUp(self)
        self.model=CorrectionModel();self.w=self.f.w('sam',self.model)
        self.w.command('integrity-inventory-prepare',self.data)
        self.base=self.w.command('integrity-mapping-checkpoint',self.data)
        self.original=self.read(self.base);self.previous=corrections.index(self.original['bundle']['mappings'])
        self.start_records=list(self.f.store.db.execute('SELECT * FROM records'))
        self.model.calls.clear()

    def read(self,result):return self.w.command('integrity-correction-read',dict(ref=result['ref']))
    def target(self,pair,mode='judgment'):
        return dict(packet_ref=pair[0],part_ref=pair[1],mode=mode,
            reason='The generic event assertion may not establish this named event; examine that relationship.',quote_refs=[])
    def targets(self):
        a=next(k for k,p in self.previous.items() if p['claim_interpretation']=='Record event A1.')
        b=next(k for k,p in self.previous.items() if p['claim_interpretation']=='Record event C10.')
        return [self.target(a),self.target(b,'follow-up')]
    def prepare(self,targets=None):
        return self.w.command('integrity-correction-prepare',dict(checkpoint=self.base['ref'],targets=targets or self.targets()))
    def run_plan(self,plan):return self.w.command('integrity-correction-run',dict(plan=plan['ref'],semantic=True,consent=True))

    def test_exact_targets_native_final_and_no_double_counted_usage(self):
        plan=self.prepare();result=self.run_plan(plan);body=self.read(result);after=corrections.index(body['bundle']['mappings'])
        changed={k for k in self.previous if self.previous[k]!=after[k]}
        self.assertEqual(changed,{(t['packet_ref'],t['part_ref']) for t in self.targets()})
        follow=self.targets()[1];pair=(follow['packet_ref'],follow['part_ref'])
        self.assertEqual({k for k in after[pair] if after[pair][k]!=self.previous[pair][k]},{'remaining_gap'})
        self.assertEqual(self.read(self.base),self.original)
        self.assertTrue(set(self.start_records)<=set(self.f.store.db.execute('SELECT * FROM records')))
        self.assertEqual(body['approval'],'not-granted')
        self.assertEqual(body['parent'],self.base['ref'])
        call=self.model.calls[0]['context']
        self.assertTrue(call['option_contract']['context_parts'])
        self.assertTrue(all(v['full_clause'] for v in call['option_contract']['material_parts'].values()))
        self.model.calls.clear()
        assessed=self.w.command('integrity-assess',dict(self.data,mapping_checkpoint=result['ref']))
        saved=self.f.review(assessed['ref'])['body']
        self.assertEqual([x['context']['assessment_phase'] for x in self.model.calls],['joint-comparison'])
        for pair,part in corrections.index(saved['decision_trace']).items():
            # Native final validation adds source locations and review labels.
            original=after[pair]
            canonical={k:part[k] for k in original}
            canonical['evidence_quotes']=[{k:q[k] for k in ('citation_ref','quote')} for q in part['evidence_quotes']]
            self.assertEqual(canonical,original)
        self.assertEqual(saved['token_usage']['total_tokens'],0)
        self.assertEqual(saved['decision_trace']['checkpoint_provenance']['reused_phase_receipts'][-1]['usage']['total_tokens'],110)
        self.assertEqual(saved['approval'],'not-granted')
        self.assertTrue(self.w.command('integrity-assess',dict(self.data,mapping_checkpoint=result['ref']))['cached'])
        self.assertEqual(len(self.model.calls),1)

    def test_uphold_is_valid_and_no_forced_relabel(self):
        plan=self.prepare();self.model.disposition='uphold';result=self.run_plan(plan)
        self.assertEqual(self.read(result)['bundle']['mappings'],self.original['bundle']['mappings'])
        before=len(self.model.calls)
        self.assertTrue(self.run_plan(plan)['cached']);self.assertEqual(len(self.model.calls),before)
        self.assertTrue(self.w.command('integrity-mapping-checkpoint',self.data)['cached'])
        self.assertEqual(len(self.model.calls),before)

    def test_clarification_preserves_judgment_and_holds_dependent_comparison(self):
        plan=self.prepare();self.model.disposition='clarification-required';result=self.run_plan(plan)
        self.assertEqual(result['status'],'clarification-required')
        self.assertEqual(self.read(result)['bundle']['mappings'],self.original['bundle']['mappings'])
        before=len(self.model.calls)
        with self.assertRaises(DecisionBlocked):self.w.command('integrity-assess',dict(self.data,mapping_checkpoint=result['ref']))
        self.assertEqual(len(self.model.calls),before)

    def test_duplicate_foreign_heading_and_wrong_packet_targets_rejected_offline(self):
        ctx=self.w.integrity.assemble(self.data);heading=next(iter(options.context(ctx)['context_parts']))
        bad=deepcopy(self.targets()[0]);bad['part_ref']=heading
        other=deepcopy(self.targets()[0]);other['packet_ref']='foreign:v1'
        foreign_quote=deepcopy(self.targets()[0]);foreign_quote['quote_refs']=['Q-not-in-selection']
        for targets in ([self.targets()[0]]*2,[bad],[other],[foreign_quote]):
            with self.assertRaises(ValueError):self.prepare(targets)
        self.assertEqual(self.model.calls,[])

    def test_rejects_collateral_outputs_placeholder_missing_and_invalid_quotes(self):
        plan=self.prepare()
        def extra(out,c):out['unrequested']=deepcopy(next(iter(out.values())))
        def missing(out,c):out.pop(next(iter(out)))
        def placeholder(out,c):next(iter(out.values()))['rationale']='TODO'
        def quote(out,c):next(iter(out.values()))['replacement']['evidence_quotes']=['Q-invented']
        def meaning(out,c):next(iter(out.values()))['replacement']['claim_interpretation']='A different requirement'
        def follow_grade(out,c):
            for k,t in c['correction_targets'].items():
                if t['mode']=='follow-up':out[k]['replacement']={'status':'supported'}
        for fault in (extra,missing,placeholder,quote,meaning,follow_grade):
            self.model.fault=fault
            with self.assertRaises(ValueError):self.run_plan(plan)
            self.assertEqual(self.read(self.base),self.original)
        self.assertEqual(self.w.integrity.records('integrity-correction-receipt'),[])
        self.assertFalse(any(x['context'].get('assessment_phase')=='joint-comparison' for x in self.model.calls))

    def test_changed_contract_settings_evidence_level_and_actor_prevent_reuse_before_calls(self):
        plan=self.prepare()
        with patch.object(corrections,'INSTRUCTIONS',corrections.INSTRUCTIONS+' Changed rule.'):
            with self.assertRaises(StaleBasis):self.run_plan(plan)
        with patch.object(self.model,'status',return_value=dict(provider='scripted',model='different-model')):
            with self.assertRaises(StaleBasis):self.run_plan(plan)
        with self.assertRaises(ValueError):
            self.w.command('integrity-assess',dict(self.data,mapping_checkpoint=self.base['ref'],evidence_level='operational-verification'))
        other=self.f.w('alex',self.model)
        with self.assertRaises(PermissionError):other.command('integrity-correction-run',dict(plan=plan['ref'],semantic=True,consent=True))
        self.assertEqual(self.model.calls,[])

    def test_interrupted_later_batch_reuses_successful_receipt(self):
        selected=[self.target(k) for k,p in self.previous.items() if p['status']=='supported'][:13]
        plan=self.prepare(selected);self.model.fail_batch=2
        with self.assertRaisesRegex(RuntimeError,'interrupted'):self.run_plan(plan)
        self.assertEqual(len(self.w.integrity.records('integrity-correction-receipt')),1)
        self.assertEqual(len(self.w.integrity.records('integrity-mapping-checkpoint')),1)
        result=self.run_plan(plan)
        self.assertEqual(self.model.corrections,3)
        self.assertEqual(len(self.w.integrity.records('integrity-correction-receipt')),2)
        self.assertEqual(self.read(result)['parent'],self.base['ref'])

    def test_source_and_rights_change_reject_before_generation(self):
        plan=self.prepare();original=self.w.integrity.assemble
        def changed(data):
            ctx=original(data);ctx['required_authority']['decider']='changed-owner';return ctx
        with patch.object(self.w.integrity,'assemble',side_effect=changed):
            with self.assertRaises(StaleBasis):self.run_plan(plan)
        source=self.f.store.latest('EVENT-SOURCE',self.w.scopes)
        self.f.store.put(source['ref'].id,source['kind'],source['scope'],dict(source['body'],text='Changed evidence'),source['ref'].revision)
        with self.assertRaises(StaleBasis):self.run_plan(plan)
        self.assertEqual(self.model.calls,[])

    def test_consent_is_required_and_failure_during_call_cannot_save(self):
        plan=self.prepare()
        with self.assertRaises(ValueError):self.w.command('integrity-correction-run',dict(plan=plan['ref']))
        def change(out,c):
            source=self.f.store.latest('EVENT-SOURCE',self.w.scopes)
            self.f.store.put(source['ref'].id,source['kind'],source['scope'],dict(source['body'],text='Changed evidence'),source['ref'].revision)
        self.model.fault=change
        with self.assertRaises(StaleBasis):self.run_plan(plan)
        self.assertEqual(self.w.integrity.records('integrity-correction-receipt'),[])
        self.assertEqual(len(self.w.integrity.records('integrity-mapping-checkpoint')),1)

    def test_targeted_settings_change_invalidates_completed_correction(self):
        def settings(ctx):
            return dict(max_output_tokens=self.model.target_limit if ctx.get('assessment_phase')=='targeted-correction' else 8000)
        self.model.target_limit=12000;self.model.request_settings=settings
        # This model settings identity is new, so create its own unchanged mapping checkpoint.
        self.base=self.w.command('integrity-mapping-checkpoint',self.data)
        plan=self.prepare();result=self.run_plan(plan);count=len(self.model.calls)
        self.model.target_limit=11000
        with self.assertRaises(StaleBasis):self.run_plan(plan)
        with self.assertRaises(StaleBasis):self.w.command('integrity-assess',dict(self.data,mapping_checkpoint=result['ref']))
        self.assertEqual(len(self.model.calls),count)

    def test_frozen_condition_change_invalidates_before_call(self):
        plan=self.prepare();original=self.w.integrity.assemble
        def changed(data):
            ctx=original(data)
            unit=next(iter(ctx['condition_inventory']['conditions'].values()))
            unit['meaning']='A materially different frozen meaning.'
            return ctx
        with patch.object(self.w.integrity,'assemble',side_effect=changed):
            with self.assertRaises(ValueError):self.run_plan(plan)
        self.assertEqual(self.model.calls,[])
