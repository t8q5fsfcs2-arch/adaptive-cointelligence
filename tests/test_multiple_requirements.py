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
from workbench.requirement_drafts import entries, legacy_id
from test_intake import VALUE, CONTEXT
from test_agent_runtime import RequirementTestModel


class MultipleRequirementsTests(unittest.TestCase):
    path = 'experience/accessibility'

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'multiple.sqlite3'
        self.store=Store(self.db);self.w=Workspace(self.store,'priya',RequirementTestModel());self.i=self.w.intake
        self.i.start(dict(title='Fictional multiple requirement fixture'))
        self.i.save(dict(expected=self.ref(),step='value',**VALUE));self.i.accept_value(dict(expected=self.ref(),confirm=True))
        self.i.save(dict(expected=self.ref(),step='context',**CONTEXT));self.i.build(dict(expected=self.ref()))

    def tearDown(self):
        self.store.close();self.tmp.cleanup()

    def ref(self):return asdict(self.i.draft()['ref'])
    def area(self):return select_drawer(self.i.draft()['body']['scaffold'],self.path)[0]
    def row(self,suffix,title='A focused requirement',criteria='A distinct observable check'):
        return dict(id=legacy_id(self.path)+'--'+suffix*12,title=title,requirement='Required behavior '+suffix,acceptance_criteria=criteria,included=True)
    def save(self,rows,**changes):
        scaffold=deepcopy(self.i.draft()['body']['scaffold']);area=select_drawer(scaffold,self.path)[0]
        area.update(requirements=rows,**changes)
        return self.i.save_drawers(dict(expected=self.ref(),drawers=scaffold))
    def seed_legacy(self):
        ds=self.i.draft()['body']['scaffold'];area=select_drawer(ds,self.path)[0]
        area.update(requirement='Existing authored requirement',acceptance_criteria='Existing acceptance check')
        self.i.save_drawers(dict(expected=self.ref(),drawers=ds))
    def publish(self):
        case=self.i.request(dict(expected=self.ref(),confirm=True))['id']
        for actor in ('sam','maya'):
            Intake(self.store,actor).review(dict(expected=asdict(self.i.latest(case)['ref']),disposition='ready-for-investigation',rationale='Fictional review'))
        self.i.publish(dict(expected=asdict(self.i.latest(case)['ref']),confirm=True,rationale='Fictional direction release'))
        return self.i.latest(case)

    def test_legacy_projection_is_read_only_and_retains_identity_and_wording(self):
        self.seed_legacy();before=self.i.draft();rows=entries(self.area(),self.path)
        self.assertEqual(rows[0]['id'],legacy_id(self.path));self.assertEqual(rows[0]['acceptance_criteria'],'Existing acceptance check')
        self.assertEqual(before,self.i.draft());self.assertNotIn('requirements',self.area())
        self.save(rows+[self.row('a')]);self.assertEqual(self.area()['requirement'],'Existing authored requirement')
        self.assertEqual(self.store.read(before['ref'],{PRIVATE}),before)

    def test_multiple_entries_survive_edit_reopen_and_scaffold_refresh(self):
        first,second=self.row('a','Keyboard access','Keyboard check'),self.row('b','Focus visibility','Visible focus check')
        self.save([first,second]);first_revision=self.i.draft();second['acceptance_criteria']='Refined focus check';self.save([first,second])
        self.store.close();self.store=Store(self.db);self.w=Workspace(self.store,'priya',RequirementTestModel());self.i=self.w.intake
        self.i.build(dict(expected=self.ref(),confirm=True));rows=entries(self.area(),self.path)
        self.assertEqual(rows,[first,second]);self.assertEqual(self.store.read(first_revision['ref'],{PRIVATE})['body']['scaffold'][1]['children'][0]['requirements'][1]['acceptance_criteria'],'Visible focus check')

    def test_missing_duplicate_or_cross_area_id_is_rejected_atomically(self):
        rows=[self.row('a'),self.row('b')];self.save(rows);before=self.i.draft()
        for bad in [[rows[0]],[rows[0],rows[0]],[rows[0],{**rows[1],'id':'REQ-INTAKE-needs/jobs--'+'a'*12}]]:
            with self.assertRaises(ValueError):self.save(bad)
            self.assertEqual(self.i.draft(),before)
        ds=deepcopy(before['body']['scaffold']);area=select_drawer(ds,self.path)[0];del area['requirements']
        with self.assertRaises(ValueError):self.i.save_drawers(dict(expected=self.ref(),drawers=ds))
        self.assertEqual(self.i.draft(),before)

    def test_exclusion_retains_entry_but_does_not_publish_it(self):
        first,second=self.row('a'),self.row('b');second['included']=False;self.save([first,second]);self.publish()
        self.assertIsNotNone(self.i.latest(first['id']));self.assertIsNone(self.i.latest(second['id']))
        self.assertEqual(entries(self.area(),self.path)[1],second)

    def test_publication_packet_goal_links_and_delivery_preserve_each_pair(self):
        self.w.command('goals-save',dict(expected=self.ref(),goals=[dict(id='G-one',title='Reduce task friction',outcome='Finish without avoidable effort',active=True,basis_fields=['value'])],measures=[dict(id='M-one',name='Task completion',active=True,basis_fields=['measures'],goal_ids=['G-one'])]))
        rows=[self.row('a','Keyboard completion','Complete by keyboard'),self.row('b','Visible focus','Focus remains visible')]
        self.save(rows,goal_ids=['G-one']);case=self.publish()
        packet=case['body']['result']['packet'];contents=self.store.resolve_packet(packet['id'],packet['revision'],{SCOPE})
        for item in rows:
            req=self.i.latest(item['id']);self.assertEqual(req['body']['acceptance_criteria'],item['acceptance_criteria'])
            self.assertEqual(req['body']['drawer_id'],'DRW-'+self.path);self.assertEqual(req['body']['status'],'proposed')
            self.assertEqual(req['body']['goal_refs'][0]['id'],'G-one');self.assertEqual(req['body']['measure_refs'][0]['id'],'M-one')
            self.assertIn(asdict(req['ref']),contents['refs'])
            own=self.store.resolve_packet('PKT-'+item['id'],1,{SCOPE});self.assertIn(asdict(req['ref']),own['refs'])
        for target,kind in [('jira','Story'),('ado','User Story')]:
            r=self.w.command('delivery-prepare',dict(target=target,work_item_type=kind,destination='DEMO',requirements=[asdict(self.i.latest(x['id'])['ref']) for x in rows]))
            draft=self.i.latest(r['id'])['body'];self.assertEqual(len(draft['items']),2)
            self.assertEqual([x['acceptance_criteria'] for x in draft['items']],[x['acceptance_criteria'] for x in rows]);self.assertEqual(draft['connector'],'not-connected')

    def test_republication_does_not_overwrite_shared_requirement_versions(self):
        rows=[self.row('a'),self.row('b')];self.save(rows);self.publish();before=[self.i.latest(r['id']) for r in rows]
        rows[1]['requirement']='Reconsidered private candidate';rows[1]['acceptance_criteria']='New private check'
        self.save(rows);self.publish()
        self.assertEqual([self.i.latest(r['id']) for r in rows],before)

    def test_entry_scoped_coach_and_agent_do_not_change_siblings(self):
        rows=[self.row('a','First'),self.row('b','Second')];self.save(rows)
        ctx,_=self.w.field_coach.context(dict(mode='draft',kind='requirement',id=self.path,requirement_id=rows[1]['id'],field='acceptance_criteria',expected=self.ref(),working=dict(title='Second',requirement=rows[1]['requirement'],acceptance_criteria='Working second check')))
        self.assertEqual(ctx['draft_requirement']['id'],rows[1]['id']);self.assertNotIn('requirements',ctx['area'])
        result=self.w.command('requirement-agent-run',dict(expected=self.ref(),drawer=self.path,requirement_id=rows[1]['id'],skill='draft',consent=True))
        self.w.command('requirement-agent-apply',dict(expected=self.ref(),result=result['ref'],requirement='Revised second behavior',acceptance_criteria='Revised second check',confirm=True))
        after=entries(self.area(),self.path);self.assertEqual(after[0],rows[0]);self.assertEqual(after[1]['acceptance_criteria'],'Revised second check')
        with self.assertRaises(StaleBasis):self.save_using_old_ref(result['ref'])

    def save_using_old_ref(self,old):
        # Any non-current intake reference must be rejected before writing.
        return self.i.save_drawers(dict(expected=old,drawers=self.i.draft()['body']['scaffold']))

    def test_domain_cannot_save_private_entries_and_stale_save_cannot_replace_them(self):
        old=self.ref();rows=[self.row('a'),self.row('b')];self.save(rows);ds=self.i.draft()['body']['scaffold']
        with self.assertRaises(PermissionError):Intake(self.store,'sam').save_drawers(dict(expected=self.ref(),drawers=ds))
        with self.assertRaises(StaleBasis):self.i.save_drawers(dict(expected=old,drawers=ds))
        self.assertIsNone(Intake(self.store,'sam').state()['draft'])
