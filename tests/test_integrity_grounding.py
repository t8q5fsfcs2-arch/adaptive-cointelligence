"""Quote/coordination/state guarantees. Synthetic models do not prove semantics."""
from copy import deepcopy
from unittest.mock import patch
import unittest
from workbench.integrity_example import Fixture
from workbench.integrity import model_context, citation_catalog
from workbench.integrity_options_example import synthetic_output
from workbench.decisions import SCOPE
from workbench import integrity_options as options, integrity_parts as parts
from workbench import integrity_grounding as grounding, integrity_pipeline as pipeline


class QuoteGroundingTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close);self.service=self.f.w('alex').integrity
        self.ctx=self.service.assemble(dict(packets=[self.f.a['packet']],mode='advisory',evaluation_scope='within-domain'))

    def copied_context(self):
        ctx=deepcopy(self.ctx);anchor=next(r for r in ctx['records'] if r['kind']=='requirement')
        for n in range(2):
            extra=deepcopy(anchor);extra['ref']['id']='COPY-'+str(n)
            ctx['records'].append(extra);ctx['requirements'].append(extra['ref'])
            self.f.store.put(extra['ref']['id'],'requirement',SCOPE,extra['body'])
            ctx['manifest']['included'].append(extra['ref'])
        for r in ctx['records']:
            if r['kind']=='integrity-expression':r['body']['requirements']=ctx['requirements']
        ctx['citation_catalog']=citation_catalog(ctx)
        return ctx

    def test_exact_quote_is_required_and_saved_with_source_offsets(self):
        out=synthetic_output(model_context(self.ctx))['decision']
        good,_=options.validate(self.service,out,self.ctx,[])
        quote=good['packet_findings'][0]['parts'][0]['evidence_quotes'][0]
        loc=quote['verified_location'];record=next(r for r in self.ctx['records'] if r['ref']==dict(id=loc['id'],revision=loc['revision']))
        self.assertEqual(record['body'][loc['field']][loc['start']:loc['end']],quote['quote'])
        for mutate in (lambda p:p['evidence_quotes'].clear(),
                       lambda p:p['evidence_quotes'][0].update(quote='This invented evidence is not in the packet.'),
                       lambda p:p['evidence_quotes'][0].update(citation_ref=out['packet_findings'][0]['obligation_ref'])):
            bad=deepcopy(out);mutate(bad['packet_findings'][0]['parts'][0])
            with self.assertRaises(ValueError):options.validate(self.service,bad,self.ctx,[])
        self.assertIn('awaiting-human-review',good['packet_findings'][0]['parts'][0]['support_verification'])

    def test_ambiguous_substring_is_rejected_not_assigned_arbitrary_offset(self):
        out=synthetic_output(model_context(self.ctx))['decision'];finding=out['packet_findings'][0]
        q=finding['parts'][0]['evidence_quotes'][0];ctx=deepcopy(self.ctx)
        ctx['citation_catalog'][q['citation_ref']]['quote']='Repeated. Repeated.';q['quote']='Repeated.'
        with self.assertRaisesRegex(ValueError,'unambiguously'):parts.validate_finding(finding,ctx,options.context(ctx))

    def test_overlapping_occurrences_are_also_ambiguous(self):
        out=synthetic_output(model_context(self.ctx))['decision'];finding=out['packet_findings'][0]
        q=finding['parts'][0]['evidence_quotes'][0];ctx=deepcopy(self.ctx)
        ctx['citation_catalog'][q['citation_ref']]['quote']='banana';q['quote']='ana'
        with self.assertRaisesRegex(ValueError,'unambiguously'):parts.validate_finding(finding,ctx,options.context(ctx))

    def test_quote_choices_preserve_literal_source_and_pair_with_its_citation(self):
        passage='Role-based access must be used to determine:\nWho can submit feedback\nWho can view assigned items\nWho can edit, reassign, or close feedback\n'
        choices=parts.quote_choices(passage)
        self.assertEqual(choices,[passage.strip()])
        longer='\n'.join(f'Unique observation {i}: a documentary design claim, not operational proof.' for i in range(40))
        self.assertEqual(''.join(longer.split()),''.join(''.join(q.split()) for q in parts.quote_choices(longer)))
        self.assertTrue(all(q in longer and len(q)<=600 for q in parts.quote_choices(longer)))
        wire=options.wire_schema(self.ctx);quote_schema=wire['$defs']['integrity_part_0']['anyOf'][0]['properties']['evidence_quotes']['items']
        choices=parts.quote_catalog(self.ctx,options.context(self.ctx));qid=quote_schema['enum'][0]
        options.shape(qid,quote_schema,wire)
        quote=choices[qid];self.assertEqual(self.ctx['citation_catalog'][quote['citation_ref']]['quote'][quote['start']:quote['end']],quote['quote'])
        with self.assertRaises(ValueError):options.shape('Q-invented',quote_schema,wire)
        governing=next(iter(options.context(self.ctx)['clauses']))
        with self.assertRaises(ValueError):options.shape(governing,quote_schema,wire)
        def check_enums(value):
            if isinstance(value,dict):
                if 'enum' in value:self.assertFalse(any(isinstance(v,str) and '\n' in v for v in value['enum']))
                for item in value.values():check_enums(item)
            elif isinstance(value,list):
                for item in value:check_enums(item)
        check_enums(wire)

    def test_mapping_separates_policy_from_evidence_and_retains_parent_scope(self):
        ctx=self.copied_context();batch=grounding.batches(ctx)[0]
        projected=grounding.project(grounding.subset(ctx,batch),batch)
        self.assertNotIn('source_records',projected)
        self.assertFalse(set(projected['packet_evidence']) & set(options.context(ctx)['clauses']))
        self.assertEqual(set(projected['citation_catalog']),set(projected['packet_evidence'])|set(projected['option_contract']['clauses']))
        for target in projected['governing_targets'].values():
            self.assertEqual(len(target['occurrences']),3)
            self.assertTrue(all(x['parent']['body']['text'] for x in target['occurrences']))
        unit=list(parts.catalog({'C':dict(quote='Outside scope: Fleet-wide rollout; staffing policy changes.')} ).values())[1]
        self.assertIn('Outside scope',unit['full_clause']);self.assertIn('Outside scope',unit['preceding_text'])
        with patch.object(options,'VERSION','presentation-label-only'):
            self.assertEqual(grounding.project(grounding.subset(ctx,batch),batch),projected)

    def test_separate_applicability_prevents_reuse_and_keeps_all_original_anchors(self):
        ctx=self.copied_context()
        class Model:
            def __init__(self):self.calls=[]
            def generate(self,**kw):
                self.calls.append(kw);c=kw['context'];out=synthetic_output(c,phase='investigate')
                if c['assessment_phase']=='clause-mapping':
                    out={k:out['decision'][k] for k in ('obligations','packet_findings')}
                    out['applicability']={k:dict(status='requires-separate' if len(v['occurrences'])>1 else 'shared',rationale='Synthetic differing context; assess each separately.',occurrences={x['clause_ref']:dict(status='different-or-uncertain' if len(v['occurrences'])>1 else 'same-meaning',rationale='The fixture requires separate treatment of this occurrence.') for x in v['occurrences']}) for k,v in c['governing_targets'].items()}
                else:
                    for k in ('obligations','packet_findings'):out['decision'].pop(k)
                return dict(output=out,response_id=str(len(self.calls)),model='synthetic',usage={})
        m=Model();result=pipeline.generate(self.service,m,ctx)
        self.assertEqual(len(m.calls),11)  # initial three candidate groups + nine separately assessed clauses + synthesis
        final=result['output']['decision']
        self.assertEqual({o['clause_ref'] for o in final['obligations']},set(options.context(ctx)['clauses']))
        self.assertEqual(len(final['obligations']),9)
        self.assertTrue(all(r['basis_fingerprint'] for r in result['mapping_groups']))

    def test_conflicting_judgments_survive_and_block_substantive_reliance(self):
        ctx=self.copied_context();out=synthetic_output(model_context(ctx))['decision']
        group=grounding.groups(ctx)[0];finding=next(f for f in out['packet_findings'] if f['obligation_ref']==group[1])
        finding['parts'][0].update(status='uncertain',remaining_gap='Meaning may differ in this parent context.')
        finding.update(parts.parent(finding['parts'],options.context(ctx)['material_parts']))
        # Ordering of returned parts cannot change comparison identity.
        for f in out['packet_findings']:f['parts'].reverse()
        good,extra=options.validate(self.service,out,ctx,[])
        self.assertEqual(good['consistency']['status'],'unresolved')
        self.assertEqual(len(good['consistency']['conflicts']),1)
        self.assertEqual({j['status'] for j in good['consistency']['conflicts'][0]['judgments']},{'supported','uncertain'})
        self.assertEqual(good['options'][0]['hard_gate'],'blocked');self.assertIsNone(good['recommendation']['preferred_option'])
        self.assertIn('Unresolved model disagreement',good['summary'])
        self.assertTrue(any('Repeated obligations' in reason for reason in good['options'][0]['gate_reasons']))
        self.assertTrue(any(f['key'].startswith('options:consistency:') for f in extra))


if __name__=='__main__':unittest.main()
