"""Synthetic coordination checks; never semantic evidence or a paid-model test."""
from collections import Counter
from copy import deepcopy
import unittest
from unittest.mock import patch

from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench.integrity import citation_catalog
from workbench.decisions import SCOPE
from workbench import integrity_options as options,integrity_parts as parts,integrity_grounding as grounding,integrity_pipeline as pipeline


TEXT='Operating conditions:\n'+ '\n'.join(
    ('Project rules:\n' if group=='B' else '')+'Record event '+', '.join(group+str(i) for i in range(1,11))+'.'
    for group in 'ABC')


class WindowModel:
    """Strict wire-shaped fixture, including reuse and a gap in the final window."""
    def __init__(self,separate=False,mutate=None):self.calls=[];self.separate=separate;self.mutate=mutate
    def status(self):return dict(configured=True,provider='scripted',model='condition-window-fixture')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw));c=kw['context'];phase=c.get('assessment_phase');out=synthetic_output(c)
        if phase=='condition-inventory':
            for pid,row in out['parts'].items():
                quote=c['source_units'][pid]['quote']
                if quote.startswith('Record event '):
                    row['conditions']=[dict(source_ref=pid,meaning='Record event '+event+'.') for event in quote.removeprefix('Record event ').removesuffix('.').split(', ')]
        elif phase=='clause-mapping':
            canonical=out['decision'];qchoices={v['quote']:k for k,v in c['packet_quote_choices'].items()}
            obligations={o['clause_ref']:dict(elements={k:None if e['status']=='unspecified' else e for k,e in o['elements'].items()})
                for o in canonical['obligations'] if o['clause_ref'] in c['new_interpretation_refs']}
            findings={}
            for slot,pair in c['option_contract']['required_packet_findings'].items():
                finding=next(f for f in canonical['packet_findings'] if (f['packet_ref'],f['obligation_ref'])==(pair['packet_ref'],pair['obligation_ref']))
                selected={}
                for original in finding['parts']:
                    p=deepcopy(original);pid=p.pop('part_ref');p.pop('evidence_refs')
                    if p['claim_interpretation']=='Record event C10.':
                        p.update(status='uncertain',remaining_gap='The synthetic source supplies no record for event C10.')
                        p['evidence_relationship'].update(relation='partial',missing_link='The event record does not specify event C10.',evidence_request='Inspect a record identifying event C10.')
                        if c.get('frozen_inventory'):p['entailment_check']['counterexample_possible']=True
                    if c.get('frozen_inventory'):p.pop('claim_interpretation');p.pop('support_scope')
                    p['evidence_quotes']=[qchoices[q['quote']] for q in p['evidence_quotes']]
                    selected[pid]=p
                findings[slot]=dict(parts=selected)
            applicability={}
            for rep in c['new_applicability_refs']:
                occurrences=c['governing_targets'][rep]['occurrences'];separate=self.separate and len(occurrences)>1
                applicability[rep]=dict(status='requires-separate' if separate else 'shared',
                    rationale='Synthetic context requires separate treatment.' if separate else 'Synthetic parents have identical applicable meaning.',
                    occurrences={o['clause_ref']:dict(status='different-or-uncertain' if separate else 'same-meaning',rationale='This is a declared synthetic context judgment, not semantic verification.') for o in occurrences})
            out=dict(obligations=obligations,packet_findings=findings,applicability=applicability)
        elif phase=='joint-comparison':
            for key in ('obligations','packet_findings'):out['decision'].pop(key)
        # Real providers use the same closed schema; exercise it offline too.
        options.shape(out,kw['schema'])
        # Faults reach application validation even if a provider ignores its schema.
        if self.mutate:self.mutate(out,c)
        return dict(output=out,model='scripted',response_id='fixture-'+str(len(self.calls)),usage={})


class ConditionBatchTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close)
        self.f.anchor=self.f.store.put('EVENTS','requirement',SCOPE,dict(title='Synthetic event inventory',text=TEXT,
            conditions='Keep original event identities.',acceptance_criteria='Retain every required event.',status='approved',owner='alex'))
        text='A synthetic event record is available for inspection.'
        source=self.f.store.put('EVENT-SOURCE','contribution',SCOPE,dict(title='Synthetic event evidence',text=text,owner='sam',domain='Research',status='published-for-review'))
        self.f.a=self.f.expression('sam','research','Events',text,[],source=source)
        self.model=WindowModel();self.w=self.f.w('sam',self.model)
        self.data=dict(packets=[self.f.a['packet']],evaluation_scope='within-domain',mode='advisory',semantic=True,consent=True,evidence_level='documentary-alignment')

    def frozen(self):
        self.w.command('integrity-inventory-prepare',self.data)
        return self.w.integrity.assemble(self.data)

    def test_native_route_reviews_all_conditions_retains_headings_and_last_gap(self):
        result=self.w.command('integrity-assess',self.data);body=self.f.review(result['ref'])['body'];ctx=body['context'];trace=body['decision_trace']
        self.assertEqual(len(ctx['condition_inventory']['conditions']),34)
        self.assertEqual(len(trace['context_parts']),2)
        self.assertTrue(all(v['material'] for v in ctx['condition_inventory']['conditions'].values()))
        self.assertEqual({v['quote'] for v in trace['context_parts'].values()},{'Operating conditions:','Project rules:'})
        self.assertEqual(sum(len(f['parts']) for f in trace['packet_findings']),32)
        target=next(f for f in trace['packet_findings'] if len(f['parts'])==30)
        self.assertEqual(target['status'],'uncertain')
        gap=next(p for p in target['parts'] if p['status']=='uncertain')['remaining_gap']
        self.assertIn(gap,trace['summary']);self.assertEqual(body['approval'],'not-granted')
        cards=self.w.integrity_gaps.cards(self.f.review(result['ref']))
        self.assertEqual(len(cards),1);self.assertEqual(cards[0]['missing'],gap)
        self.assertEqual(cards[0]['status'],'uncertain')
        calls=[x for x in self.model.calls if x['context'].get('assessment_phase')=='clause-mapping']
        seen=Counter()
        for call in calls:
            c=call['context'];self.assertLessEqual(len(c['option_contract']['material_parts']),12)
            seen.update(c['new_interpretation_refs'])
            for heading in c['option_contract']['context_parts'].values():
                self.assertEqual(heading['full_clause'],TEXT);self.assertFalse(heading['evidence_target'])
            for unit in c['option_contract']['material_parts'].values():
                original=ctx['condition_inventory']['conditions'][next(k for k,v in c['option_contract']['material_parts'].items() if v==unit)]
                self.assertEqual(unit,original)
        self.assertEqual(set(seen.values()),{1})
        self.assertTrue(any(x['context']['fixed_clause_interpretations'] for x in calls))
        self.assertTrue(any(x['context']['fixed_shared_applicability'] for x in calls))
        self.assertTrue(trace['interpretation_receipts'])

    def test_projection_is_narrow_and_never_removes_inline_or_unknown_actions(self):
        for text in ('Project rules: Record the owner.','The operating conditions:','Owner approval:','Project rules:; Record the owner.'):
            units=parts.catalog({'C':dict(quote=text)});material,headings=parts.review_projection(units)
            self.assertEqual(material,units);self.assertFalse(headings)
        text='  Operating conditions:  \nRetain the owner.'
        units=parts.catalog({'C':dict(quote=text)});material,headings=parts.review_projection(units)
        self.assertEqual(len(headings),1);self.assertEqual(len(material),1)
        self.assertEqual(next(iter(material.values()))['preceding_text'],'  Operating conditions:  \n')

    def test_heading_only_clause_requires_clarification(self):
        ctx=self.w.integrity.assemble(self.data);cid=next(k for k,v in ctx['citation_catalog'].items() if v['field']=='text' and v['id']=='EVENTS')
        ctx['citation_catalog'][cid]['quote']='Project rules:'
        with self.assertRaisesRegex(ValueError,'only a section heading'):pipeline.plan(ctx)

    def test_boundaries_cover_arbitrary_sizes_without_renumbering(self):
        ctx=self.frozen();original=deepcopy(ctx);c=options.context(ctx)
        for limit in (1,7,12,24):
            windows=grounding.review_batches(ctx,limit);seen=[]
            for window in windows:
                self.assertTrue(0<len(window['part_refs'])<=limit);seen.extend(window['part_refs'])
            self.assertEqual(Counter(seen),Counter(c['material_parts'].keys()))
        self.assertEqual(ctx,original)
        for limit in (0,-1,True):
            with self.assertRaises(ValueError):grounding.review_batches(ctx,limit)

    def test_missing_duplicate_and_foreign_windows_cannot_reach_synthesis(self):
        ctx=self.frozen();windows=grounding.review_batches(ctx)
        variants=[windows[:-1],windows+[windows[0]]]
        wrong=deepcopy(windows);wrong[0]['part_refs'][0]='C-foreign/P1';variants.append(wrong)
        for corrupt in variants:
            model=WindowModel()
            with patch.object(grounding,'review_batches',return_value=corrupt):
                with self.assertRaises(ValueError):pipeline.generate(self.w.integrity,model,ctx)
            self.assertEqual(model.calls,[])

    def test_missing_or_foreign_model_parts_cannot_reach_synthesis(self):
        ctx=self.frozen()
        for replace in (False,True):
            def mutate(out,c):
                if c.get('assessment_phase')=='clause-mapping':
                    selected=next(iter(out['packet_findings'].values()))['parts'];pid=next(iter(selected));value=selected.pop(pid)
                    if replace:selected['C-foreign/P1']=value
            model=WindowModel(mutate=mutate)
            with self.assertRaises(ValueError):pipeline.generate(self.w.integrity,model,ctx)
            self.assertFalse(any(c['context'].get('assessment_phase')=='joint-comparison' for c in model.calls))

    def test_model_cannot_resubmit_a_cached_interpretation_or_applicability(self):
        ctx=self.frozen()
        for field in ('obligations','applicability'):
            def mutate(out,c):
                if c.get('assessment_phase')=='clause-mapping' and c['fixed_clause_interpretations']:
                    cid=next(iter(c['fixed_clause_interpretations']));out[field][cid]={}
            with self.assertRaises(ValueError):pipeline.generate(self.w.integrity,WindowModel(mutate=mutate),ctx)

    def copied_context(self):
        # Raw synthetic spans exercise original-occurrence fallback independently
        # of inventory extraction. Actual grading uses the frozen native test above.
        ctx=self.w.integrity.assemble(self.data)
        row=next(r for r in ctx['records'] if r['ref']['id']=='EVENTS')
        row['body']['text']='\n'.join('Record synthetic event '+str(i)+'.' for i in range(31))
        for n in range(2):
            extra=deepcopy(row);extra['ref']['id']='COPY-'+str(n)
            ctx['records'].append(extra);ctx['requirements'].append(extra['ref']);ctx['manifest']['included'].append(extra['ref'])
        for record in ctx['records']:
            if record['kind']=='integrity-expression':record['body']['requirements']=ctx['requirements']
        ctx['citation_catalog']=citation_catalog(ctx)
        return ctx

    def test_rejected_shared_candidate_is_not_retried_for_later_windows(self):
        ctx=self.copied_context()
        model=WindowModel(separate=True);result=pipeline.generate(self.w.integrity,model,ctx)
        seen=Counter();candidates=Counter()
        for call in model.calls:
            c=call['context']
            if c.get('assessment_phase')!='clause-mapping':continue
            for rep,target in c['governing_targets'].items():
                if len(target['occurrences'])>1:candidates[rep]+=1
                else:seen.update(k for k,v in c['option_contract']['material_parts'].items() if v['clause_ref']==rep)
        self.assertEqual(set(candidates.values()),{1})
        self.assertEqual(Counter(options.context(ctx)['material_parts'].keys()),seen)
        self.assertEqual(len(result['output']['decision']['obligations']),9)

    def test_confirmed_shared_windows_keep_every_original_condition(self):
        ctx=self.copied_context();model=WindowModel();result=pipeline.generate(self.w.integrity,model,ctx)
        actual=[p['part_ref'] for f in result['output']['decision']['packet_findings'] for p in f['parts']]
        self.assertEqual(Counter(actual),Counter(options.context(ctx)['material_parts'].keys()))
        new_applicability=Counter()
        for call in model.calls:
            c=call['context']
            if c.get('assessment_phase')=='clause-mapping':new_applicability.update(c['new_applicability_refs'])
        self.assertEqual(set(new_applicability.values()),{1})
        self.assertTrue(any(g['applicability_reused'] for g in result['mapping_groups']))

    def test_two_packets_each_receive_all_conditions_and_keep_separate_gaps(self):
        text='A different synthetic design record is available for inspection.'
        source=self.f.store.put('EVENT-DESIGN','contribution',SCOPE,dict(title='Synthetic design evidence',text=text,owner='lee',domain='Design',status='published-for-review'))
        design=self.f.expression('lee','design','Events design',text,[],source=source)
        data={**self.data,'packets':[self.f.a['packet'],design['packet']],'evaluation_scope':'cross-domain'}
        workspace=self.f.w('alex',self.model);result=workspace.command('integrity-assess',data)
        review=self.f.review(result['ref']);trace=review['body']['decision_trace']
        by_packet=Counter()
        for finding in trace['packet_findings']:by_packet[finding['packet_ref']]+=len(finding['parts'])
        self.assertEqual(sorted(by_packet.values()),[32,32])
        cards=workspace.integrity_gaps.cards(review)
        self.assertEqual(len(cards),2);self.assertEqual({c['status'] for c in cards},{'uncertain'})


if __name__=='__main__':unittest.main()
