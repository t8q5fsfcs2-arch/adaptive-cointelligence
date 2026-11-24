from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.intake import Intake, PRIVATE
from workbench.workspace import Workspace
from workbench.scaffold import select_drawer
from test_intake import VALUE, CONTEXT
from test_agent_runtime import RequirementTestModel

class DefaultScaffoldVisibilityTests(unittest.TestCase):
    def test_inspecting_a_project_without_intake_exposes_templates_without_writing_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / 'synthetic.sqlite3')
            try:
                before = store.db.execute('SELECT * FROM records ORDER BY rowid').fetchall()
                state = Intake(store, 'priya').state()
                self.assertIsNone(state['draft'])
                self.assertIsNone(state['profile'])
                self.assertEqual(len(state['scaffold_defaults']), 6)
                self.assertEqual(sum(len(d['children']) for d in state['scaffold_defaults']), 19)
                self.assertEqual(store.db.execute('SELECT * FROM records ORDER BY rowid').fetchall(), before)
            finally:
                store.close()

class HierarchyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'synthetic.sqlite3')
        self.i=Intake(self.store,'priya');self.i.start({'title':'Synthetic hierarchy test'})
        self.i.save(dict(expected=self.ref(),step='value',**VALUE))
        self.i.accept_value(dict(expected=self.ref(),confirm=True))
        self.i.save(dict(expected=self.ref(),step='context',**CONTEXT))
        self.build()
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.i.draft()['ref'])
    def build(self):self.i.build(dict(expected=self.ref(),confirm=True))
    def child(self):return select_drawer(self.i.draft()['body']['scaffold'],'experience/accessibility')[0]
    def configure(self,edit,actor='priya'):
        p=self.i.profile();body=deepcopy(p['body']);edit(body)
        return Intake(self.store,actor).configure(dict(expected=asdict(p['ref']),name=body['name'],drawers=body['drawers']))
    def save_child(self,**values):
        ds=self.i.draft()['body']['scaffold'];select_drawer(ds,'experience/accessibility')[0].update(values)
        self.i.save_drawers(dict(expected=self.ref(),drawers=ds))
    def publish(self):
        case=self.i.request(dict(expected=self.ref(),confirm=True))['id']
        for actor in ('sam','maya'):
            Intake(self.store,actor).review(dict(expected=asdict(self.i.latest(case)['ref']),disposition='ready-for-investigation',rationale='Synthetic review'))
        return self.i.publish(dict(expected=asdict(self.i.latest(case)['ref']),confirm=True,rationale='Synthetic direction'))
    def test_default_has_specific_criteria_without_claiming_completion(self):
        ds=self.i.draft()['body']['scaffold'];self.assertEqual(len(ds),6)
        self.assertEqual(sum(len(d['children']) for d in ds),19)
        c=self.child();self.assertIn('keyboard',c['criteria']);self.assertIn('WCAG 2.2',c['references'])
        self.assertTrue(c['evidence'] and c['revisit']);self.assertEqual(c['requirement'],'')
        self.assertNotIn('passed',c)
    def test_refresh_updates_criteria_preserves_work_and_earlier_versions(self):
        self.save_child(requirement='A user can operate the task with a keyboard.',acceptance_criteria='Complete the task without a pointer.',question='Custom local question')
        before=self.i.draft()
        self.configure(lambda b:b['drawers'][1]['children'][0].update(criteria='New SME criterion'))
        self.assertFalse(self.i.state()['scaffold_current']);self.build()
        c=self.child();self.assertEqual(c['criteria'],'New SME criterion')
        self.assertEqual(c['question'],'Custom local question');self.assertEqual(c['requirement'],'A user can operate the task with a keyboard.')
        self.assertEqual(self.store.read(before['ref'],{PRIVATE})['body'],before['body'])
    def test_category_lead_can_only_configure_own_areas(self):
        self.configure(lambda b:b['drawers'][1]['children'][0].update(criteria='SME-specific criterion'),actor='sam')
        self.assertEqual(self.i.profile()['body']['changed_by'],'sam')
        self.assertIsNone(Intake(self.store,'sam').state()['draft'])
        before=self.i.profile()['ref']
        for edit in (lambda b:b['drawers'][2].update(question='Unauthorized'),lambda b:b['drawers'][1].update(owner='maya'),lambda b:b.update(name='Unauthorized')):
            with self.assertRaises(PermissionError):self.configure(edit,actor='sam')
        self.assertEqual(self.i.profile()['ref'],before)
    def test_invalid_structure_is_atomic(self):
        before=self.i.profile()['ref']
        mutations=[lambda b:b['drawers'][1]['children'].append(deepcopy(b['drawers'][1]['children'][0])),lambda b:b['drawers'][1]['children'][0].update(criteria=''),lambda b:b['drawers'][1]['children'][0].update(children=[{'key':'too-deep'}])]
        for edit in mutations:
            with self.assertRaises(ValueError):self.configure(edit)
        self.assertEqual(self.i.profile()['ref'],before)
    def test_exclusion_requires_reason_and_disabled_area_cannot_be_bypassed(self):
        with self.assertRaises(ValueError):self.save_child(included=False)
        self.save_child(included=False,exclusion_reason='Another confirmed scope covers this area')
        self.configure(lambda b:b['drawers'][1]['children'][0].update(when='disabled'));self.build()
        ds=self.i.draft()['body']['scaffold'];ds[1]['children'][0]['included']=True
        with self.assertRaises(ValueError):self.i.save_drawers(dict(expected=self.ref(),drawers=ds))
    def test_agent_receives_exact_area_criteria_and_apply_is_isolated(self):
        model=RequirementTestModel();w=Workspace(self.store,'priya',model);before=self.i.draft()['body']['scaffold']
        result=w.command('requirement-agent-run',dict(expected=self.ref(),drawer='experience/accessibility',skill='draft',consent=True))
        ctx=model.calls[0]['context'];self.assertEqual(ctx['drawer']['criteria'],self.child()['criteria'])
        self.assertEqual(ctx['category']['label'],'Experience and usability');self.assertEqual(ctx['drawer_path'],'experience/accessibility')
        self.assertIn('SME review criteria',model.calls[0]['instructions'])
        self.assertEqual(self.i.draft()['body']['scaffold'],before)
        w.command('requirement-agent-apply',dict(result=result['ref'],expected=self.ref(),requirement='Reviewed synthetic requirement',acceptance_criteria='Observable test',confirm=True))
        after=self.i.draft()['body']['scaffold'];self.assertEqual(after[1]['children'][0]['requirement'],'Reviewed synthetic requirement')
        self.assertEqual(after[1]['children'][1:],before[1]['children'][1:]);self.assertEqual(after[0],before[0])
    def test_changed_sme_criteria_block_old_assistant_result(self):
        w=Workspace(self.store,'priya',RequirementTestModel())
        result=w.command('requirement-agent-run',dict(expected=self.ref(),drawer='experience/accessibility',skill='draft',consent=True))
        self.configure(lambda b:b['drawers'][1]['children'][0].update(criteria='Revised test basis'))
        with self.assertRaises(StaleBasis):w.command('requirement-agent-apply',dict(result=result['ref'],expected=self.ref(),requirement='Old basis',acceptance_criteria='Old check',confirm=True))
        self.build()
        with self.assertRaises(StaleBasis):w.command('requirement-agent-apply',dict(result=result['ref'],expected=self.ref(),requirement='Old basis',acceptance_criteria='Old check',confirm=True))
    def test_publish_links_child_requirement_and_retirement_preserves_history(self):
        self.save_child(requirement='Keyboard operation is supported.',acceptance_criteria='Complete representative tasks without a pointer.')
        self.publish();child=self.i.latest('DRW-experience/accessibility');req=self.i.latest('REQ-INTAKE-experience/accessibility')
        self.assertEqual(child['body']['parent_id'],'DRW-experience')
        self.assertEqual(req['body']['drawer_id'],child['ref'].id);self.assertEqual(req['body']['status'],'proposed')
        self.assertIn(child['ref'],list(self.store.graph({SCOPE}).successors(req['ref'])))
        self.configure(lambda b:b['drawers'][1]['children'][0].update(when='disabled'));self.build();self.publish()
        self.assertEqual(self.i.latest(child['ref'].id)['body']['status'],'retired')
        self.assertEqual(self.i.latest(req['ref'].id),req)
        self.assertEqual(self.store.read(child['ref'],{SCOPE})['body'],child['body'])
        self.assertIn(req['ref'].id,Workspace(self.store,'alex').state()['requirement_impacts'])
    def test_legacy_flat_profile_remains_valid(self):
        self.configure(lambda b:[d.pop('children',None) for d in b['drawers']]);self.build()
        self.assertTrue(all(not d['children'] for d in self.i.draft()['body']['scaffold']))
        self.publish();self.assertEqual(len([r for r in Workspace(self.store,'alex').state()['records'] if r['kind']=='requirement-drawer']),6)
