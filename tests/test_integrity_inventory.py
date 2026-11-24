"""Frozen-question and evidence-level invariants; explicitly scripted, no network."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench.integrity import model_context
from workbench.decisions import SCOPE
from workbench.core import StaleBasis
from workbench import integrity_inventory as inventory,integrity_options as options,integrity_parts as parts,integrity_grounding as grounding
from workbench.integrity_explanations import explanation

TARGET='A permitted submitter can inspect the current owner, current status, next step and resolution note.'
FOCI=('current owner','current status','next step','resolution note')

class InventoryModel:
    def __init__(self):self.calls=[];self.cap=10000;self.reject_review=False;self.mutate_grade=None;self.before_review=None
    def status(self):return dict(configured=True,provider='scripted',model='fixed-condition-fixture')
    def request_settings(self,ctx):return dict(max_output_tokens=self.cap)
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));ctx=kw['context'];phase=ctx.get('assessment_phase');out=synthetic_output(ctx)
        if phase=='condition-inventory':
            for pid,row in out['parts'].items():
                if ctx['source_units'][pid]['quote']==TARGET:
                    row['conditions']=[dict(source_ref=pid,meaning='A permitted submitter can inspect the '+focus+'.') for focus in FOCI]
                    row['coverage_rationale']='Four visible fields are individually retained with the shared permitted-submitter qualifier.'
        elif phase=='condition-inventory-review':
            if self.before_review:self.before_review()
            if self.reject_review:
                next(iter(out['parts'].values())).update(complete=False,faithful=False,omissions=['The next-step visibility condition was omitted.'])
        else:
            for finding in out['decision']['packet_findings']:
                for p in finding['parts']:
                    if ctx['option_contract']['material_parts'][p['part_ref']].get('meaning')=='A permitted submitter can inspect the next step.':
                        p.update(status='uncertain',remaining_gap='The selected source does not establish that the next step is visible.')
                        p['evidence_relationship'].update(relation='partial',missing_link='The next-step visibility is not established.',evidence_request='Provide documentary coverage of the next-step visibility.')
                        p['entailment_check']=dict(counterexample_possible=True,explanation='Owner, status and resolution may be visible while the next step remains hidden.')
                finding.update(parts.parent(finding['parts'],ctx['option_contract']['material_parts']))
            if self.mutate_grade:self.mutate_grade(out)
        return dict(output=out,model='scripted',response_id='scripted-'+str(len(self.calls)),usage={})


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close)
        self.f.anchor=self.f.store.put('VISIBILITY','requirement',SCOPE,dict(title='Visible feedback fields',text=TARGET,
            conditions='Use role-based viewing.',acceptance_criteria='Retain the permitted submitter scope.',status='approved',owner='alex'))
        text='Permitted submitters can inspect current owner, current status and resolution note.'
        source=self.f.store.put('VISIBLE-SOURCE','contribution',SCOPE,dict(text=text,title='Synthetic documented intent',domain='Research',owner='sam',status='published-for-review'))
        self.f.a=self.f.expression('sam','research','Scheduling',text,[],source=source)
        self.model=InventoryModel();self.w=self.f.w('sam',self.model)
        self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True,evidence_level='documentary-alignment')

    def assess(self):return self.w.command('integrity-assess',self.data)
    def context(self):return self.w.integrity.assemble(self.data)

    def test_actual_route_freezes_before_grading_and_keeps_every_condition_gap(self):
        result=self.assess();body=self.f.review(result['ref'])['body'];ctx=body['context']
        self.assertEqual([x['context'].get('assessment_phase') for x in self.model.calls],['condition-inventory','condition-inventory-review',None])
        for call in self.model.calls[:2]:
            self.assertNotIn('packet_evidence',call['context']);self.assertNotIn('source_records',call['context']);self.assertNotIn('domain_expressions',call['context'])
        units=[v for v in ctx['condition_inventory']['conditions'].values() if v['parent_source']['quote']==TARGET]
        self.assertEqual({v['quote'] for v in units},{TARGET})
        self.assertEqual(len({v['source_ref'] for v in units}),1)
        self.assertEqual(len({v['meaning'] for v in units}),4)
        self.assertTrue(all(v['meaning'].startswith('A permitted submitter can inspect') for v in units))
        finding=next(f for f in body['decision_trace']['packet_findings'] if len(f['parts'])==4)
        self.assertEqual(finding['status'],'uncertain');self.assertEqual(len(finding['parts']),4)
        gap=next(p['remaining_gap'] for p in finding['parts'] if p['status']=='uncertain')
        self.assertIn(gap,body['summary']);self.assertIn(gap,' '.join(body['decision_trace']['recommendation']['conditions']))
        saved=self.f.review(ctx['condition_inventory']['ref'])['body']
        self.assertEqual(saved['state'],'frozen-for-evaluation');self.assertEqual(saved['approval'],'not-granted')
        self.assertEqual(body['approval'],'not-granted')

    def test_source_reference_rejects_unknown_cross_unit_and_free_text_locators(self):
        ctx=self.context();batch=grounding.batches(ctx)[0];projected,schema=inventory.request(ctx,batch)
        raw=self.model.generate(context=projected,schema=schema,instructions=inventory.PREPARE)['output']
        pid=next(iter(raw['parts']));other=next(k for k in projected['source_units'] if k!=pid)
        for value in ('not-a-source-unit',other):
            bad=deepcopy(raw);bad['parts'][pid]['conditions'][0]['source_ref']=value
            with self.assertRaises(ValueError):inventory.decode(ctx,batch,bad)
        bad=deepcopy(raw);bad['parts'][pid]['conditions'][0]['focus']='Paraphrased quotation.'
        with self.assertRaises(ValueError):inventory.decode(ctx,batch,bad)
        bad=deepcopy(raw);bad['parts'][pid]['conditions'][0].pop('source_ref')
        with self.assertRaises(ValueError):inventory.decode(ctx,batch,bad)

    def test_conditions_share_exact_source_anchor_without_changing_model_meaning(self):
        ctx=self.context();batch=grounding.batches(ctx)[0];projected,schema=inventory.request(ctx,batch)
        raw=self.model.generate(context=projected,schema=schema,instructions=inventory.PREPARE)['output']
        decoded=inventory.decode(ctx,batch,raw)
        for value in decoded.values():
            parent=projected['source_units'][value['source_ref']]
            self.assertEqual(value['quote'],parent['quote'])
            self.assertEqual(value['quote'],parent['full_clause'][value['start']:value['end']])
            self.assertIn(value['meaning'],[v['meaning'] for v in raw['parts'][value['source_ref']]['conditions']])
        visible=[v for v in decoded.values() if v['quote']==TARGET]
        self.assertEqual(len(visible),4)
        self.assertEqual({v['meaning'] for v in visible},{'A permitted submitter can inspect the '+f+'.' for f in FOCI})

    def test_alternative_meaning_survives_reference_resolution_and_freeze(self):
        requirement=self.f.store.read(self.f.anchor,{SCOPE})
        alternative='Each proposed metric records an event or calculation.'
        self.f.anchor=self.f.store.put('ALTERNATIVE','requirement',SCOPE,
            {**requirement['body'],'title':'Alternative metric basis','text':alternative})
        source=self.f.store.put('ALTERNATIVE-SOURCE','contribution',SCOPE,
            dict(title='Alternative basis',text=alternative,domain='Research',owner='sam',status='published-for-review'))
        self.f.a=self.f.expression('sam','research','Alternative basis',alternative,[],source=source)
        self.data['packets']=[self.f.a['packet']]
        self.w.command('integrity-inventory-prepare',self.data)
        values=[v for v in self.context()['condition_inventory']['conditions'].values() if v['quote']==alternative]
        self.assertEqual(len(values),1)
        self.assertEqual(values[0]['meaning'],alternative)
        self.assertEqual(values[0]['source_ref'],values[0]['parent_part_ref'])

    def test_repeated_grading_reuses_inventory_while_level_change_gets_separate_basis(self):
        a=self.assess();old=self.f.review(a['ref'])['body']['context']['condition_inventory']
        self.assertTrue(self.assess()['cached']);self.assertEqual(len(self.model.calls),3)
        self.model.cap+=1;b=self.assess()
        self.assertEqual(len(self.model.calls),4)
        self.assertEqual(self.f.review(b['ref'])['body']['context']['condition_inventory'],old)
        self.data['evidence_level']='operational-verification';c=self.assess()
        new=self.f.review(c['ref'])['body']['context']['condition_inventory']
        self.assertNotEqual(new['ref'],old['ref']);self.assertEqual(len(self.model.calls),7)
        self.assertEqual(self.f.review(a['ref'])['body']['context']['evidence_level'],'documentary-alignment')

    def test_rejected_inventory_never_reaches_evidence_grading(self):
        self.model.reject_review=True
        with self.assertRaisesRegex(ValueError,'inventory review is unresolved'):self.assess()
        self.assertEqual(len(self.model.calls),2)
        self.assertFalse(self.w.integrity.records('integrity-condition-inventory'));self.assertFalse(self.w.integrity.records('integrity-assessment'))
        receipt=self.w.integrity.records('agent-execution')[0]['body']
        self.assertEqual(receipt['status'],'failed');self.assertEqual(len(receipt['phases']),2)

    def test_fidelity_review_separates_source_limits_from_blocking_defects(self):
        schema=inventory.review_schema({'unit':{}})
        row=dict(complete=True,faithful=True,rationale='The supplied source meaning is preserved.',omissions=[],
            source_limitations=['The source does not specify which implementation supplies this behavior.'])
        options.shape(dict(parts={'unit':row}),schema)
        bad=deepcopy(row);bad['omissions']=['A required condition is missing.']
        with self.assertRaises(ValueError):options.shape(dict(parts={'unit':bad}),schema)
        bad=deepcopy(row);bad['faithful']=False
        with self.assertRaises(ValueError):options.shape(dict(parts={'unit':bad}),schema)
        bad['omissions']=['The model changed the alternative into two requirements.']
        options.shape(dict(parts={'unit':bad}),schema)

    def test_source_change_during_preparation_stops_freeze(self):
        def change():
            r=self.f.store.read(self.f.anchor,{SCOPE})
            self.f.store.put(r['ref'].id,'requirement',SCOPE,{**r['body'],'text':'A changed governing question.'},r['ref'].revision)
        self.model.before_review=change
        with self.assertRaises(StaleBasis):self.assess()
        self.assertFalse(self.w.integrity.records('integrity-condition-inventory'));self.assertFalse(self.w.integrity.records('integrity-assessment'))

    def test_frozen_claim_and_evidence_level_cannot_be_replaced(self):
        self.w.command('integrity-inventory-prepare',self.data);ctx=self.context()
        base=synthetic_output(model_context(ctx))['decision']
        for field,value in [('claim_interpretation','A weaker comparable status is visible.'),('evidence_level','operational-verification'),('support_scope','Any convenient evidence level is acceptable.')]:
            bad=deepcopy(base);bad['packet_findings'][0]['parts'][0][field]=value
            with self.assertRaises(ValueError):options.validate(self.w.integrity,bad,ctx,[])
        bad=deepcopy(base);bad['packet_findings'][0]['parts'][0]['entailment_check']['counterexample_possible']=True
        with self.assertRaisesRegex(ValueError,'counterexample'):options.validate(self.w.integrity,bad,ctx,[])
        bad=deepcopy(base);next(f for f in bad['packet_findings'] if len(f['parts'])==4)['parts'].pop()
        with self.assertRaisesRegex(ValueError,'every material part'):options.validate(self.w.integrity,bad,ctx,[])

    def test_wire_selects_condition_ids_without_model_authored_replacement_claims(self):
        self.w.command('integrity-inventory-prepare',self.data);ctx=self.context();wire=options.wire_schema(ctx)
        for definition in wire['$defs'].values():
            for variant in definition.get('anyOf',[]):
                props=variant.get('properties',{})
                if 'evidence_quotes' in props:
                    self.assertNotIn('claim_interpretation',props);self.assertNotIn('support_scope',props)
                    self.assertEqual(props['evidence_level']['enum'],['documentary-alignment'])
        out=synthetic_output(model_context(ctx))['decision'];slots=options.packet_slots(ctx);q=parts.quote_catalog(ctx,options.context(ctx))
        out['packet_findings']={slot:dict(parts={p['part_ref']:{k:v for k,v in p.items() if k not in ('part_ref','evidence_refs','claim_interpretation','support_scope')} for p in next(f for f in out['packet_findings'] if all(f[k]==v for k,v in pair.items()))['parts']}) for slot,pair in slots.items()}
        for f in out['packet_findings'].values():
            for p in f['parts'].values():p['evidence_quotes']=[next(key for key,v in q.items() if v['citation_ref']==e['citation_ref'] and v['quote']==e['quote']) for e in p['evidence_quotes']]
        decoded=options.normalize_wire(out,ctx)
        for f in decoded['packet_findings']:
            for p in f['parts']:self.assertEqual(p['claim_interpretation'],options.context(ctx)['material_parts'][p['part_ref']]['meaning'])
        next(iter(next(iter(out['packet_findings'].values()))['parts'].values()))['claim_interpretation']='A weakened claim.'
        with self.assertRaisesRegex(ValueError,'replace a frozen'):options.normalize_wire(out,ctx)

    def test_placeholder_grade_is_rejected_without_assessment_or_fabricated_gap(self):
        def placeholder(out):
            for f in out['decision']['packet_findings']:
                for p in f['parts']:
                    if p['status']=='uncertain':p['remaining_gap']='/'
        self.model.mutate_grade=placeholder
        with self.assertRaisesRegex(ValueError,'Placeholder'):self.assess()
        self.assertFalse(self.w.integrity.records('integrity-assessment'))
        self.assertTrue(self.w.integrity.records('integrity-condition-inventory'))
        self.assertEqual(next(r for r in self.w.integrity.records('agent-execution') if r['body']['skill']=='integrity-review')['body']['status'],'failed')
        for value in ('/','—','...','N/A','TBD','Unknown.','See above','123'):
            with self.subTest(value=value),self.assertRaises(ValueError):explanation(value)

    def test_shared_reuse_needs_every_original_occurrence_and_consent_precedes_models(self):
        batch=[['one','two']];item=dict(status='shared',rationale='These source conditions have the same applicable meaning.',
            occurrences={'one':dict(status='same-meaning',rationale='This occurrence preserves the required meaning.')})
        with self.assertRaises(ValueError):grounding.validate_applicability({'one':item},batch)
        item['occurrences']['two']=dict(status='different-or-uncertain',rationale='The parent changes this occurrence meaning.')
        with self.assertRaisesRegex(ValueError,'every original'):grounding.validate_applicability({'one':item},batch)
        self.data['consent']=False
        with self.assertRaises(ValueError):self.assess()
        self.assertEqual(self.model.calls,[])
        self.data.update(consent=True,evidence_level='model-chooses')
        with self.assertRaisesRegex(ValueError,'Declare'):self.assess()
        self.assertEqual(self.model.calls,[])


if __name__=='__main__':unittest.main()
