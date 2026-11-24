from copy import deepcopy
from dataclasses import asdict
import unittest
import test_scaffold_hierarchy as hierarchy
from workbench.workspace import Workspace
from workbench.scaffold import select_drawer
from workbench.scaffold_tailoring import ScaffoldTailoring
from workbench.intake import Intake, PRIVATE
from workbench.core import StaleBasis
from workbench.decisions import SCOPE
from workbench.model_provider import ModelUnavailable

class TailorModel:
    def __init__(self):self.calls=[];self.mutate=None;self.on_call=None
    def status(self):return dict(configured=True,provider='test',model='synthetic')
    def generate(self,*,context,instructions,schema):
        self.calls.append(deepcopy(context))
        out=dict(summary='Synthetic project tailoring',areas=[dict(path=a['path'],relevance='applies',
            rationale='The stated users need to resume their enrollment task.',question='Can enrollment users resume after an interruption?',
            checks=['Resume the saved step without losing entered information.'],gaps=['Confirm the retention period.'],basis_fields=['need'],
            requirement_ids=[context['requirements'][0]['ref']['id']] if context['requirements'] else []) for a in context['areas']],uncovered_needs=[])
        if self.mutate:self.mutate(out)
        if self.on_call:self.on_call()
        return dict(output=out,model='synthetic',usage={'total_tokens':20})

class TailoringTests(unittest.TestCase):
    setUp=hierarchy.HierarchyTests.setUp
    tearDown=hierarchy.HierarchyTests.tearDown
    ref=hierarchy.HierarchyTests.ref
    build=hierarchy.HierarchyTests.build
    configure=hierarchy.HierarchyTests.configure
    def run_tailor(self,model=None,**data):
        self.model=model or TailorModel();self.w=Workspace(self.store,'priya',self.model)
        return self.w.command('scaffold-tailor',{**dict(expected=self.ref(),consent=True),**data})
    def apply(self,r,**data):
        return self.w.command('scaffold-tailor-apply',{**dict(result=r['ref'],expected=self.ref(),selected=['experience/accessibility'],confirm=True),**data})
    def test_full_context_and_versioned_apply_preserve_requirements_and_sme_rules(self):
        self.store.put('REQ-TEST','requirement',SCOPE,dict(title='Synthetic business requirement',text='Users can resume enrollment',status='proposed'))
        before=deepcopy(self.i.draft());r=self.run_tailor(category='experience')
        self.assertEqual(len(self.model.calls[0]['areas']),5);self.assertEqual(self.model.calls[0]['requirements'][0]['body']['status'],'proposed')
        self.assertEqual(self.i.draft(),before)
        self.apply(r);after=self.i.draft();old=select_drawer(before['body']['scaffold'],'experience/accessibility')[0];new=select_drawer(after['body']['scaffold'],'experience/accessibility')[0]
        self.assertEqual(new['criteria'],old['criteria']);self.assertEqual(new['requirement'],old['requirement']);self.assertEqual(new['included'],old['included'])
        self.assertEqual(new['project_focus']['requirement_ids'],['REQ-TEST']);self.assertEqual(new['project_focus']['basis_values']['need'],before['body']['values']['need'])
        self.assertNotIn('project_focus',select_drawer(after['body']['scaffold'],'experience/ease-of-use')[0])
        self.assertEqual(self.store.read(before['ref'],{PRIVATE}),before)
        self.assertEqual(self.w.state()['agent_monitoring']['runs'][0]['mode'],'simulated')
    def test_unknown_or_duplicate_area_and_false_references_rejected(self):
        edits=[lambda o:o['areas'][0].update(path='invented'),lambda o:o['areas'][1].update(path=o['areas'][0]['path']),lambda o:o['areas'][0].update(basis_fields=['invented']),lambda o:o['areas'][0].update(requirement_ids=['private-id']),lambda o:o['areas'][0].update(basis_fields=[],requirement_ids=[]),lambda o:o['areas'][0].update(relevance='uncertain',gaps=[]),lambda o:o['areas'][0].update(relevance='outside-scope')]
        for edit in edits:
            model=TailorModel();model.mutate=edit
            with self.assertRaises(ModelUnavailable):self.run_tailor(model,category='experience')
        self.assertFalse(self.w.scaffold_tailoring.state()['runs'])
    def test_changes_during_execution_or_before_apply_invalidate(self):
        r=self.run_tailor();self.i.save(dict(expected=self.ref(),step='context',constraints='Changed boundary'))
        with self.assertRaises(StaleBasis):self.apply(r)
        self.build();model=TailorModel();model.on_call=lambda:self.i.save(dict(expected=self.ref(),step='context',constraints='A newer boundary'))
        with self.assertRaises(StaleBasis):self.run_tailor(model)
    def test_new_requirement_and_profile_revision_invalidate_proposals(self):
        r=self.run_tailor();self.store.put('REQ-NEW','requirement',SCOPE,dict(text='New synthetic requirement',status='proposed'))
        with self.assertRaises(StaleBasis):self.apply(r)
        r=self.run_tailor();self.configure(lambda b:b['drawers'][1]['children'][0].update(criteria='Revised SME criteria'))
        with self.assertRaises(StaleBasis):self.apply(r)
    def test_scope_advice_never_removes_an_area(self):
        m=TailorModel();m.mutate=lambda o:o['areas'][0].update(relevance='outside-scope',basis_fields=['out_scope'])
        r=self.run_tailor(m,category='experience');self.apply(r)
        self.assertTrue(select_drawer(self.i.draft()['body']['scaffold'],'experience/accessibility')[0]['included'])
    def test_inline_edits_retained_and_changed_intent_blocks_old_focus(self):
        r=self.run_tailor();self.apply(r);drawers=self.i.draft()['body']['scaffold'];c=select_drawer(drawers,'experience/accessibility')[0]
        c.update(project_question='Edited question',project_rationale='Edited rationale',project_checks='Edited check',project_gaps='Open threshold')
        self.i.save_drawers(dict(expected=self.ref(),drawers=drawers));self.assertEqual(select_drawer(self.i.draft()['body']['scaffold'],'experience/accessibility')[0]['project_focus']['checks'],'Edited check')
        self.i.save(dict(expected=self.ref(),step='context',constraints='New boundary'));self.build()
        self.assertIn('experience/accessibility',self.w.scaffold_tailoring.state()['stale_areas'])
        with self.assertRaises(StaleBasis):self.w.requirement_agent.current(self.ref(),'experience/accessibility')
    def test_rights_consent_and_selection_guards(self):
        for actor in ('sam','maya','alex'):
            w=Workspace(self.store,actor,TailorModel());self.assertIsNone(w.scaffold_tailoring.state())
            with self.assertRaises(PermissionError):w.command('scaffold-tailor',dict(expected=self.ref(),consent=True))
        with self.assertRaises(ValueError):self.run_tailor(consent=False)
        r=self.run_tailor()
        with self.assertRaises(ValueError):self.apply(r,selected=['bogus'])
        self.apply(r)
        with self.assertRaises(StaleBasis):self.apply(r)

    def test_downstream_finding_reopens_intent_and_stales_project_guidance(self):
        hierarchy.HierarchyTests.publish(self)
        r=self.run_tailor(category='experience');self.apply(r)
        published=self.i.latest('INT-001')
        finding=self.store.put('FIND-SYNTHETIC','contribution',SCOPE,dict(title='Interrupted task study',observation='Users lose progress',source='Synthetic research',limitation='Small synthetic sample'))
        request=Intake(self.store,'sam').refinements.create(dict(base_intent=asdict(published['ref']),source=asdict(finding),field='need',proposed_value='Retain task progress across interruptions.',rationale='Synthetic downstream finding changes the stated need.',requirement_refs=[]))
        self.assertEqual(self.i.latest('INT-001'),published)
        self.i.refinements.adopt(dict(expected=asdict(self.i.latest(request['id'])['ref']),draft_expected=self.ref(),response='Retain task progress across interruptions.',rationale='Test the revised need with the affected users.'))
        self.build()
        self.assertIn('experience/accessibility',self.w.scaffold_tailoring.state()['stale_areas'])
        self.assertEqual(self.i.latest('INT-001'),published)
        with self.assertRaises(StaleBasis):self.w.requirement_agent.current(self.ref(),'experience/accessibility')

    def test_failed_retry_does_not_reuse_previous_model_output(self):
        self.run_tailor(category='experience')
        agent=self.w.scaffold_tailoring.agent
        self.assertIsNotNone(agent.last_result)
        def unavailable(**kwargs):raise ModelUnavailable('Synthetic provider timeout')
        agent.model.generate=unavailable
        with self.assertRaises(ModelUnavailable):
            self.w.command('scaffold-tailor',dict(expected=self.ref(),consent=True,category='experience'))
        self.assertIsNone(agent.last_result)
        latest=self.w.state()['agent_monitoring']['runs'][0]
        self.assertEqual(latest['status'],'failed')
        self.assertFalse(latest.get('output'))

    def test_review_pass_uses_original_basis_and_records_both_executions(self):
        r=self.run_tailor(category='experience')
        self.assertEqual(len(self.model.calls),2)
        self.assertNotIn('candidate',self.model.calls[0])
        self.assertIn('candidate',self.model.calls[1])
        self.assertEqual(self.model.calls[0]['values'],self.model.calls[1]['values'])
        body=self.w.scaffold_tailoring.state()['runs'][0]['body']
        self.assertIsNotNone(body['preparation_execution'])
        executions=self.w.state()['agent_monitoring']['runs']
        self.assertEqual([x['skill'] for x in executions[:2]],['review-scaffold','tailor-scaffold'])
        self.assertEqual([x['status'] for x in executions[:2]],['succeeded','succeeded'])

    def test_review_failure_never_promotes_initial_draft(self):
        model=TailorModel()
        def fail_review():
            if len(model.calls)==2:raise ModelUnavailable('Synthetic review failure')
        model.on_call=fail_review
        with self.assertRaises(ModelUnavailable):self.run_tailor(model,category='experience')
        self.assertFalse(self.w.scaffold_tailoring.state()['runs'])
        runs=self.w.state()['agent_monitoring']['runs']
        self.assertEqual(runs[0]['status'],'failed')
        self.assertEqual(runs[1]['status'],'succeeded')
