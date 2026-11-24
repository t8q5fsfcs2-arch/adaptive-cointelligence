"""Offline contract/lineage tests, not live semantic-quality evidence."""
from copy import deepcopy
from dataclasses import asdict
import unittest
from unittest.mock import patch
from workbench.integrity_example import Fixture
from workbench.integrity_options_example import SimulatedOptionsModel, synthetic_output
from workbench.integrity import model_context
from workbench import integrity_options as options, integrity_relationship as relationship
from workbench import integrity_grounding as grounding, integrity_parts as parts


class RelationshipTests(unittest.TestCase):
    def record(self, required, assertion, connection, relation, grade):
        return dict(status=grade, evidence_quotes=[dict(citation_ref='selected-source',quote=assertion)],
            evidence_relationship=dict(required_relationship=required,source_assertion=assertion,
                connection=connection,relation=relation,unstated_premise='',
                missing_link='The specified relationship remains unestablished in this selected passage.',
                evidence_request='Provide a source that explicitly establishes the missing relationship.'))

    def test_four_calibration_examples_reject_incompatible_labels(self):
        # Authored expected judgments; code validates the declared relationship,
        # not the truth of these interpretations. No operating facts implied.
        rows=[('Return-to-service decisions are excluded.','Manufacturer dispensation permits exceeding a limit.',
               'The passage does not identify a return-to-service decision or its scope.','adjacent-only','absent'),
              ('Reassignment records a reason.','Reassigned is a transient marker on the audit trail.',
               'The same event is recorded but its reason is unspecified.','partial','uncertain'),
              ('Providing clinical instructions is excluded.','Billing and referral feedback channels are excluded.',
               'Channel names do not establish their relationship to instruction provision.','adjacent-only','absent'),
              ('Regulatory sign-offs are excluded.','The manufacturer may grant a dispensation.',
               'No regulatory authority or sign-off relationship is asserted.','adjacent-only','absent')]
        for row in rows:
            p=self.record(*row)
            with self.subTest(required=row[0]):
                relationship.validate(p)
                p['status']='uncertain' if row[-1]=='absent' else 'absent'
                with self.assertRaisesRegex(ValueError,'Grade disagrees'):relationship.validate(p)

    def test_placeholder_missing_link_and_uncited_partial_evidence_rejected(self):
        p=self.record('Reassignment records a reason.','Reassignment enters an audit trail.',
                      'The same event is recorded but the reason is missing.','partial','uncertain')
        for key in ('required_relationship','source_assertion','connection','missing_link','evidence_request'):
            bad=deepcopy(p);bad['evidence_relationship'][key]='TBD'
            with self.subTest(key=key),self.assertRaises(ValueError):relationship.validate(bad)
        p['evidence_quotes']=[]
        with self.assertRaisesRegex(ValueError,'exact source'):relationship.validate(p)

    def test_full_support_cannot_depend_on_unstated_premise(self):
        p=self.record('Reassignment records a reason.','Every reassignment records its reason.',
                      'The source states the same required recording behavior.','full','supported')
        p['evidence_relationship'].update(missing_link='',evidence_request='')
        relationship.validate(p)
        p['evidence_relationship']['unstated_premise']='Assume reassignment means closure.'
        with self.assertRaisesRegex(ValueError,'unstated premise'):relationship.validate(p)


class FollowUpTests(unittest.TestCase):
    def setUp(self):
        self.f=Fixture();self.addCleanup(self.f.store.close)
        self.m=SimulatedOptionsModel(phase='investigate');self.w=self.f.w('alex',self.m)
        self.original=dict(packets=[self.f.a['packet']],mode='advisory',evaluation_scope='within-domain',semantic=True,consent=True)
        self.old=self.w.command('integrity-assess',self.original)
        self.original_record=deepcopy(self.f.review(self.old['ref']))
        oldsource=self.f.current('SOURCE-sam')
        source=self.f.store.put(oldsource['ref'].id,'contribution',oldsource['scope'],
            {**oldsource['body'],'text':'Validate qualification at assignment and propose an execution recheck.'},oldsource['ref'].revision)
        self.new=self.f.expression('sam','research','Follow-up',
            'Validate qualification at assignment and propose an execution recheck.',['assignment'],
            previous=self.f.a['ref'],source=source)
        self.data=dict(self.original,packets=[self.new['packet']],previous_assessment=self.old['ref'],
            revisit_reason=dict(kind='changed-evidence',detail='The revised contribution proposes an execution recheck.'))

    def test_native_followup_preserves_original_and_sends_prior_judgments(self):
        ctx=self.w.integrity.assemble(self.data);c=options.context(ctx)
        self.assertEqual(ctx['predecessors'][0]['ref'],self.f.a['ref'])
        self.assertEqual(ctx['follow_up']['previous_assessment'],self.old['ref'])
        self.assertEqual(ctx['condition_inventory'],self.original_record['body']['context']['condition_inventory'])
        for window in grounding.review_batches(ctx):
            projected=grounding.project(grounding.subset(ctx,window['groups'],window['part_refs']),window['groups'])
            seen={p for rows in projected['follow_up']['judgments'].values() for p in rows}
            self.assertEqual(seen,set(window['part_refs']))
        result=self.w.command('integrity-assess',self.data)
        current=self.f.review(result['ref'])
        self.assertEqual(self.f.review(self.old['ref']),self.original_record)
        self.assertTrue(all(p['change_review']['outcome']=='uphold' for f in current['body']['decision_trace']['packet_findings'] for p in f['parts']))
        self.assertEqual(current['body']['approval'],'not-granted')

    def test_missing_relationship_or_change_record_rejected_by_native_validator(self):
        ctx=self.w.integrity.assemble(self.data);base=synthetic_output(model_context(ctx),phase='investigate')['decision']
        for field in ('evidence_relationship','change_review'):
            bad=deepcopy(base);bad['packet_findings'][0]['parts'][0].pop(field)
            with self.subTest(field=field),self.assertRaises(ValueError):options.validate(self.w.integrity,bad,ctx,[])
        bad=deepcopy(base);f=bad['packet_findings'][0];p=f['parts'][0]
        p.update(status='absent');p['evidence_relationship']['relation']='adjacent-only'
        p['change_review']['outcome']='uphold';f.update(parts.parent(f['parts'],options.context(ctx)['material_parts']))
        with self.assertRaisesRegex(ValueError,'silently uphold'):options.validate(self.w.integrity,bad,ctx,[])
        p['change_review'].update(outcome='revise',reason_type='prior-error',explanation='The earlier grade mistook topical overlap for partial support.')
        options.validate(self.w.integrity,bad,ctx,[])

    def test_unrelated_packet_missing_trigger_and_changed_level_rejected_before_model(self):
        calls=self.m.calls
        variants=[dict(self.data,packets=[self.f.b['packet']]),dict(self.data,revisit_reason={}),
                  dict(self.data,evidence_level='operational-verification')]
        for data in variants:
            with self.assertRaises(ValueError):self.w.command('integrity-assess',data)
        self.assertEqual(self.m.calls,calls)

    def test_method_change_requires_explicit_history_only_compatibility(self):
        with patch('workbench.integrity.INSTRUCTIONS','A changed method contract.'):
            with self.assertRaises(ValueError):self.w.integrity.assemble(self.data)
            data=dict(self.data,method_change_reason='Reconsider these old grades under the new contract; no automatic reuse.')
            ctx=self.w.integrity.assemble(data)
            self.assertTrue(ctx['follow_up']['method_changed'])
            self.assertIn('no cross-basis',ctx['follow_up']['compatibility'])

    def test_history_is_not_promoted_into_evidence_catalog(self):
        ctx=self.w.integrity.assemble(self.data)
        self.assertNotIn(self.old['ref'],[dict(id=v['id'],revision=v['revision']) for v in ctx['citation_catalog'].values()])
        self.assertTrue(all(len(g)==1 for g in grounding.groups(ctx)))

    def test_private_history_cannot_enter_a_shared_review(self):
        private_scope=next(x for x in self.f.w('sam').scopes if x!='project:demo')
        ref=self.f.store.put('PRIVATE-HISTORY','integrity-assessment',private_scope,self.original_record['body'])
        before=self.m.calls
        with self.assertRaises(PermissionError):
            self.w.command('integrity-assess',dict(self.data,previous_assessment=asdict(ref)))
        self.assertEqual(self.m.calls,before)

    def test_changed_contract_cannot_reuse_old_assessment(self):
        legacy=deepcopy(self.original_record)
        legacy['body']['context'].pop('grading_contract_version')
        reasons=self.w.integrity.freshness(legacy,for_current_use=False)
        self.assertTrue(any('Grading relationship contract' in r.get('reason','') for r in reasons))


if __name__=='__main__':unittest.main()
