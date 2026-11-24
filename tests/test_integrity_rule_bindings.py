"""Application inheritance invariants, scripted model contracts only; no paid calls."""
from copy import deepcopy
import json
import unittest

from workbench.core import Ref, StaleBasis
from workbench.decisions import SCOPE, fingerprint
from workbench.integrity import model_context
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import synthetic_output
from workbench import integrity_inventory as inventory, integrity_options as options
from workbench import integrity_grounding as grounding, integrity_rule_bindings as rules

LOCAL = 'An unknown destination reaches default triage.'
LIMITS = ('Use nonurgent feedback only. Existing systems retain authoritative records. '
          'Outside scope: emergency response; replacement of authoritative systems; external ticket writes.')


class ScriptedModel:
    def __init__(self):
        self.calls = []; self.reject_exception = False

    def status(self):
        return dict(configured=True, provider='scripted', model='rule-binding-fixture')

    def generate(self, **request):
        self.calls.append(deepcopy(request)); ctx = request['context']; out = synthetic_output(ctx)
        if ctx.get('assessment_phase') == 'condition-inventory' and self.reject_exception:
            row = next(v for k,v in out['parts'].items() if ctx['source_units'][k]['quote'] == LOCAL)
            row['conditions'][0]['meaning'] = 'Default triage may write external tickets despite the source restriction.'
        if ctx.get('assessment_phase') == 'condition-inventory-review' and self.reject_exception:
            # Deliberate negative fixture: validates enforcement of rejection,
            # not a claim that the live model will reliably detect this meaning.
            key = next(k for k,v in ctx['source_units'].items() if v['quote'] == LOCAL)
            out['parts'][key].update(complete=False, faithful=False,
                omissions=['The candidate invents permission to write external tickets contrary to its linked rule.'])
        return dict(output=out, model='scripted', response_id='fixture-'+str(len(self.calls)), usage={})


class RuleBindingTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture(); self.addCleanup(self.f.store.close)
        self.f.anchor = self.f.store.put('TRIAGE','requirement',SCOPE,
            dict(title='Route unknown destinations',text=LOCAL,conditions=LIMITS,
                 acceptance_criteria='The receiving queue is visible.',status='proposed',owner='alex',execution='not-authorized'))
        source = self.f.store.put('TRIAGE-SOURCE','contribution',SCOPE,
            dict(title='Synthetic routing proposal',text=LOCAL,domain='Research',owner='sam',status='published-for-review'))
        self.expression = self.f.expression('sam','research','Routing',LOCAL,[],source=source)
        self.model = ScriptedModel(); self.w = self.f.w('sam',self.model)
        self.data = dict(packets=[self.expression['packet']],evaluation_scope='within-domain',mode='advisory',
                         semantic=True,consent=True,evidence_level='documentary-alignment')

    def prepare(self):
        return self.w.command('integrity-inventory-prepare',self.data)

    def context(self):
        return self.w.integrity.assemble(self.data)

    def test_native_inventory_keeps_short_local_meaning_and_exact_resolved_parent_rules(self):
        self.prepare(); ctx = self.context(); saved = ctx['condition_inventory']
        unit = next(x for x in saved['conditions'].values() if x['quote'] == LOCAL)
        self.assertEqual(unit['meaning'],LOCAL)
        self.assertEqual(len(unit['inherited_rule_refs']),1)
        rid = unit['inherited_rule_refs'][0]; rule = saved['rule_bindings']['rule_sets'][rid]
        self.assertEqual(rule['quote'],LIMITS)
        self.assertEqual(rule['source'],dict(id='TRIAGE',revision=1,field='conditions'))
        self.assertEqual(rule['authority']['status'],'proposed')
        self.assertEqual(rule['authority']['execution'],'not-authorized')
        extracted, checked = [x['context'] for x in self.model.calls]
        self.assertEqual(extracted['rule_bindings'],checked['rule_bindings'])
        self.assertEqual(checked['candidate_bindings'],extracted['source_unit_bindings'])
        self.assertNotIn('packet_evidence',checked)
        self.assertIn('do not rewrite', self.model.calls[0]['instructions'].lower())

    def test_direct_bounded_and_final_contexts_resolve_same_effective_meaning_without_evidence_promotion(self):
        self.prepare(); ctx = self.context(); direct = model_context(ctx)
        self.assertEqual(direct['option_contract']['rule_bindings'],ctx['condition_inventory']['rule_bindings'])
        for batch in grounding.batches(ctx):
            bounded = grounding.project(grounding.subset(ctx,batch),batch)
            contract = bounded['option_contract']; linked = contract['rule_bindings']
            for unit in contract['material_parts'].values():
                rules.validate_unit(unit,linked)
                self.assertTrue(all(ref in linked['rule_sets'] for ref in unit['inherited_rule_refs']))
            self.assertFalse(set(linked['rule_sets']) & set(bounded['packet_evidence']))
            self.assertFalse(set(linked['rule_sets']) & set(bounded['packet_quote_choices']))
        # The final phase uses this same native model_context projection.
        self.assertEqual(model_context(ctx)['option_contract']['rule_bindings'],direct['option_contract']['rule_bindings'])

    def test_missing_stale_modified_and_reassigned_rule_links_are_rejected_before_grading(self):
        result = self.prepare(); record = self.f.store.read(Ref(**result['ref']),self.w.scopes)
        original = deepcopy(record['body']); rid = next(iter(original['rule_bindings']['rule_sets']))
        def missing(body): body['rule_bindings']['rule_sets'].pop(rid)
        def changed(body): body['rule_bindings']['rule_sets'][rid]['quote'] = 'External ticket writes are allowed.'
        def stale(body): body['rule_bindings']['rule_sets'][rid]['source']['revision'] = 999
        def unbound(body): next(iter(body['conditions'].values()))['inherited_rule_refs'] = []
        def waived(body): next(iter(body['rule_bindings']['clause_bindings'].values())).clear()
        for mutate in (missing,changed,stale,unbound,waived):
            bad = deepcopy(original); mutate(bad); bad['payload_fingerprint'] = fingerprint(bad['conditions'])
            self.f.store.db.execute('UPDATE records SET body=? WHERE id=? AND revision=?',
                (json.dumps(bad),result['ref']['id'],result['ref']['revision']))
            with self.subTest(mutation=mutate.__name__), self.assertRaises(StaleBasis):
                self.w.command('integrity-assess',self.data)
            self.assertEqual(len(self.model.calls),2)
        self.f.store.db.execute('UPDATE records SET body=? WHERE id=? AND revision=?',
            (json.dumps(original),result['ref']['id'],result['ref']['revision']))

    def test_projected_catalog_removal_is_rejected_instead_of_silently_rebuilt(self):
        self.prepare(); ctx = self.context(); bad = deepcopy(ctx)
        bad['condition_inventory'].pop('rule_bindings')
        with self.assertRaises(StaleBasis):model_context(bad)
        bad = deepcopy(ctx); bad['condition_inventory']['rule_bindings']['rule_sets'].clear()
        with self.assertRaises(StaleBasis):grounding.project(bad,grounding.batches(ctx)[0])

    def test_model_cannot_remove_links_or_claim_an_authorized_exception(self):
        ctx = self.context(); batch = grounding.batches(ctx)[0]; projected,spec = inventory.request(ctx,batch)
        out = synthetic_output(projected)
        next(iter(out['parts'].values()))['conditions'][0]['inherited_rule_refs'] = []
        with self.assertRaises(ValueError):inventory.decode(ctx,batch,out)
        self.model.reject_exception = True
        with self.assertRaisesRegex(ValueError,'inventory review is unresolved'):self.prepare()
        self.assertEqual(len(self.model.calls),2)
        self.assertFalse(self.w.integrity.records('integrity-condition-inventory'))
        self.assertFalse(self.w.integrity.records('integrity-assessment'))
        self.assertEqual(self.f.store.read(self.f.anchor,self.w.scopes)['body']['conditions'],LIMITS)

    def test_changed_rule_basis_invalidates_only_its_selected_dependency_and_retains_historical_basis(self):
        self.prepare(); old = self.context(); old_id = inventory.identity(old)
        self.f.store.put('UNRELATED','source',SCOPE,dict(text='Unrelated new information.'))
        self.assertEqual(inventory.identity(self.context()),old_id)
        altered = deepcopy(old); altered.pop('condition_inventory')
        row = next(r for r in altered['records'] if r['ref']['id']=='TRIAGE')
        row['body']['conditions'] += ' Additional rule: manual exception review is required.'
        # Exact-version mutation is an adversarial fixture; a real edit appends a
        # revision. The source/binding fingerprints must detect either change.
        self.assertNotEqual(inventory.identity(altered),old_id)
        self.assertEqual(inventory.identity(old),old_id)
        self.assertEqual(self.context()['condition_inventory'],old['condition_inventory'])

    def test_same_local_words_with_different_parent_limits_are_not_grouped_for_reuse(self):
        ctx = self.context(); c = options.context(ctx)
        local = next(k for k,v in c['clauses'].items() if v['quote']==LOCAL)
        changed = deepcopy(ctx); parent = next(r for r in changed['records'] if r['ref']['id']=='TRIAGE')
        parent['body']['conditions'] = 'External ticket writes require a separate authorized decision.'
        other = options.context(changed)
        self.assertNotEqual(rules.semantic_key(c['rule_bindings'],local),rules.semantic_key(other['rule_bindings'],local))
        self.assertNotEqual(rules.binding(c['rule_bindings'],local)['rule_binding_fingerprint'],
                            rules.binding(other['rule_bindings'],local)['rule_binding_fingerprint'])

    def test_successful_review_and_cache_reuse_retain_rules_and_do_not_ratify(self):
        result = self.w.command('integrity-assess',self.data)
        assessment = self.f.review(result['ref'])['body']; count = len(self.model.calls)
        self.assertEqual(assessment['approval'],'not-granted')
        self.assertTrue(assessment['decision_trace']['condition_inventory']['rule_bindings']['rule_sets'])
        self.assertTrue(self.w.command('integrity-assess',self.data)['cached'])
        self.assertEqual(len(self.model.calls),count)


if __name__ == '__main__':
    unittest.main()
