from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.intake import Intake, PRIVATE
from workbench.workspace import Workspace
from workbench.goals import GOAL_FIELDS, MEASURE_FIELDS, snapshot
from workbench.scaffold import select_drawer
from workbench.model_provider import ModelUnavailable
from workbench.agent_runs import monitoring
from test_intake import VALUE, CONTEXT

class GoalsTestModel:
    def __init__(self): self.calls=[]; self.during=None; self.bad=None; self.fail=False
    def status(self): return dict(configured=True,provider='TEST DOUBLE',model='fake')
    def generate(self,**kw):
        self.calls.append(deepcopy(kw))
        if self.during: self.during()
        if self.fail: raise ModelUnavailable('Synthetic provider failure')
        g={k:'' for k in GOAL_FIELDS};g.update(key='G1',title='Reduce repeated effort',outcome='Customers resume without repeating completed work',beneficiary='Customers',rationale='Supports the promised reduction in effort; effect to validate',basis_fields=['value','jobs'],area_paths=['experience/accessibility','experience/usability'])
        # Use the actual configured paths, not assumed fixture taxonomy.
        g['area_paths']=[a['path'] for a in kw['context']['areas'] if a['path'].startswith('experience/')][:2]
        m={k:'' for k in MEASURE_FIELDS};m.update(key='M1',name='Completion rate',goal_keys=['G1'],basis_fields=['measures'])
        out=dict(summary='Proposed outcome and a measure with unresolved measurement details.',goals=[g],measures=[m])
        if self.bad:self.bad(out)
        return dict(output=out,model='fake',usage=dict(input_tokens=30,output_tokens=20,total_tokens=50))

class GoalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path)
        self.model=GoalsTestModel();self.w=Workspace(self.store,'priya',self.model);self.i=self.w.intake
        self.i.start({'title':'Synthetic goals project'});self.i.save(dict(expected=self.ref(),step='value',**VALUE));self.i.accept_value(dict(expected=self.ref(),confirm=True));self.i.save(dict(expected=self.ref(),step='context',**CONTEXT));self.i.build(dict(expected=self.ref()))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def ref(self):return asdict(self.i.draft()['ref'])
    def catalog(self):return snapshot(self.i,self.i.draft()['body'])
    def payload(self):return {g:[dict(id=x['id'],**x['body']) for x in items] for g,items in self.catalog().items()}
    def prepare(self):return self.w.command('goals-prepare',dict(expected=self.ref(),consent=True))
    def apply(self,r):return self.w.command('goals-apply',dict(expected=self.ref(),result=r['ref'],confirm=True))
    def save(self,p):return self.w.command('goals-save',dict(expected=self.ref(),**p))
    def publish(self):
        c=self.i.request(dict(expected=self.ref(),confirm=True))['id']
        for actor in ('sam','maya'):Intake(self.store,actor).review(dict(expected=asdict(self.i.latest(c)['ref']),disposition='ready-for-investigation',rationale='Synthetic review'))
        return self.i.publish(dict(expected=asdict(self.i.latest(c)['ref']),confirm=True,rationale='Synthetic direction'))
    def test_source_question_catalog_uses_native_question_ids_without_exposing_private_answers(self):
        data=Intake(self.store,'sam').state()
        questions={q['field']:q for q in data['source_questions']}
        self.assertEqual(questions['measures']['id'],'q17')
        self.assertEqual(questions['measure_review']['id'],'q18')
        self.assertEqual(questions['pain_points']['legacy_field'],'bottlenecks')
        self.assertIsNone(data['draft'])
        self.assertTrue(all(set(q)=={'id','title','field','legacy_field'} for q in data['source_questions']))
        self.assertEqual(self.model.calls,[])

    def test_model_proposes_reviewable_drafts_and_records_actual_execution_mode(self):
        before=self.ref();r=self.prepare();self.assertEqual(self.ref(),before)
        self.assertIn('Applicable methods',self.model.calls[0]['instructions'])
        self.apply(r);c=self.catalog();self.assertEqual(len(c['goals']),1);self.assertEqual(c['measures'][0]['body']['baseline'],'')
        self.assertEqual(c['measures'][0]['body']['goal_ids'],[c['goals'][0]['id']])
        self.assertEqual(c['goals'][0]['body']['source_intake'],before)
        run=monitoring(self.store,'priya')['runs'][0];self.assertEqual(run['mode'],'simulated');self.assertEqual(run['skill'],'prepare-goals');self.assertTrue(run['applied'])
        self.assertIsNone(self.i.latest('INT-001'))
        with self.assertRaises(StaleBasis):self.apply(r)
    def test_edit_preserves_history_and_survives_restart(self):
        self.apply(self.prepare());old=self.catalog()['goals'][0];p=self.payload();p['goals'][0]['outcome']='Human-refined outcome';self.save(p)
        self.assertEqual(self.store.read(Ref(**old['ref']),{PRIVATE})['body'],old['body'])
        refs={g:[x['ref'] for x in items] for g,items in self.catalog().items()};self.save(self.payload());self.assertEqual(refs,{g:[x['ref'] for x in items] for g,items in self.catalog().items()})
        self.store.close();self.store=Store(self.path);self.w=Workspace(self.store,'priya',self.model);self.i=self.w.intake
        self.assertEqual(self.catalog()['goals'][0]['body']['outcome'],'Human-refined outcome')
    def test_scaffold_goal_save_is_atomic_and_links_survive_refresh(self):
        self.apply(self.prepare());c=self.catalog();g=c['goals'][0]['id'];ds=self.i.draft()['body']['scaffold'];ds[0]['goal_ids']=[g]
        p=self.payload();p['goals'][0]['outcome']='Atomic edit';ds[0]['owner']='unknown';before=self.ref();old=self.catalog()
        with self.assertRaises(ValueError):self.i.save_drawers(dict(expected=self.ref(),drawers=ds,goals_catalog=p))
        self.assertEqual(self.ref(),before);self.assertEqual(self.catalog(),old)
        ds[0]['owner']='sam';self.i.save_drawers(dict(expected=self.ref(),drawers=ds,goals_catalog=p));self.i.build(dict(expected=self.ref(),confirm=True))
        self.assertEqual(self.i.draft()['body']['scaffold'][0]['goal_ids'],[g]);self.assertEqual(self.catalog()['goals'][0]['body']['outcome'],'Atomic edit')
        # Legacy callers omitting goal_ids must not erase saved links.
        ds=self.i.draft()['body']['scaffold'];del ds[0]['goal_ids'];self.i.save_drawers(dict(expected=self.ref(),drawers=ds));self.assertEqual(self.i.draft()['body']['scaffold'][0]['goal_ids'],[g])
    def test_publication_pins_many_to_many_links_and_retains_unchanged_versions(self):
        self.apply(self.prepare());p=self.payload();p['goals'].append(dict(id='G-independent',title='Independent goal',outcome='Another outcome',active=True,basis_fields=['value']));p['measures'].append(dict(id='M-independent',name='Independent measure',active=True,goal_ids=['G-independent'],basis_fields=['measures']));self.save(p)
        ds=self.i.draft()['body']['scaffold'];linked=[d for parent in ds for d in parent.get('children',[]) if d.get('goal_ids')]
        self.assertEqual(len(linked),2)
        for d in linked:d.update(requirement='Retain completed work',acceptance_criteria='Resume and inspect saved progress')
        self.i.save_drawers(dict(expected=self.ref(),drawers=ds));self.publish();g=self.catalog()['goals'][0]['id'];m=self.catalog()['measures'][0]['id'];old=self.i.latest(g);independent=self.i.latest('G-independent');oldmeasure=self.i.latest(m)
        reqs=[r for r in Workspace(self.store,'alex').state()['records'] if r['kind']=='requirement'];self.assertEqual(len(reqs),2)
        for r in reqs:
            self.assertEqual(r['body']['goal_refs'],[asdict(old['ref'])]);self.assertEqual(r['body']['measure_refs'],[asdict(oldmeasure['ref'])]);self.assertIn(old['ref'],self.store.graph({SCOPE}).successors(r['ref']))
        p=self.payload();p['measures'][0]['target']='Owner supplied target';self.save(p)
        self.assertEqual(self.i.latest(g),old);self.publish();self.assertEqual(self.i.latest('G-independent'),independent);self.assertNotEqual(self.i.latest(g)['ref'],old['ref'])
        state=Workspace(self.store,'alex').state()
        for r in reqs:
            changes=state['requirement_impacts'][r['ref'].id];self.assertIn(g,[x['previous']['id'] for x in changes]);self.assertIn(m,[x['previous']['id'] for x in changes])
            packet=self.store.resolve_packet('PKT-'+r['ref'].id,1,{SCOPE});self.assertIn(old,[x for x in packet['records'] if x['kind']=='goal'])
        self.assertEqual(self.i.latest(m)['body']['definition'],'');self.assertEqual(self.i.latest(m)['body']['outcome_status'],'not-evaluated')
    def test_private_drafts_and_unknown_targets_never_become_verified_evidence(self):
        self.apply(self.prepare());s=Workspace(self.store,'sam').state();self.assertIsNone(s['goals']);self.assertFalse(any(r['kind'].endswith('-draft') and r['kind'].startswith(('goal','success-measure')) for r in s['records']))
        with self.assertRaises(PermissionError):Workspace(self.store,'sam').command('goals-save',dict(expected=self.ref(),**self.payload()))
        self.publish();g=self.i.latest(self.catalog()['goals'][0]['id']);self.assertEqual(g['body']['status'],'agreed-for-investigation');self.assertEqual(g['body']['outcome_status'],'not-evaluated')
    def test_changed_intake_marks_only_affected_sources_and_requires_review(self):
        self.apply(self.prepare());p=self.payload();p['goals'].append(dict(id='G-other',title='Other',outcome='Other outcome',basis_fields=['why_now']));self.save(p)
        self.i.save(dict(expected=self.ref(),step='value',value='New promised benefit'));self.i.accept_value(dict(expected=self.ref(),confirm=True,rationale='Reconsidered the updated benefit'));self.i.build(dict(expected=self.ref(),confirm=True))
        s=self.w.goals.state();self.assertIn('value',s['goals'][0]['changed_fields']);self.assertEqual(s['goals'][1]['changed_fields'],[])
        with self.assertRaises(StaleBasis):self.i.request(dict(expected=self.ref(),confirm=True))
        p=self.payload();p['goals'][0]['review_basis']=True;self.save(p);self.i.request(dict(expected=self.ref(),confirm=True))
    def test_stale_configuration_and_provider_failures_leave_draft_unchanged(self):
        before=self.ref();self.model.fail=True
        with self.assertRaises(ModelUnavailable):self.prepare()
        self.assertEqual(self.ref(),before);self.assertEqual(monitoring(self.store,'priya')['runs'][0]['status'],'failed')
        self.model.fail=False;r=self.prepare();self.i.save(dict(expected=self.ref(),step='success',measures='A changed measure'))
        with self.assertRaises(StaleBasis):self.apply(r)
        self.i.build(dict(expected=self.ref(),confirm=True));self.model.during=lambda:self.i.save(dict(expected=self.ref(),step='success',measures='Changed during generation'))
        with self.assertRaises(StaleBasis):self.prepare()
        self.assertEqual(self.catalog(),{'goals':[],'measures':[]})
    def test_invalid_proposals_never_apply_and_invalid_saves_rollback(self):
        for bad in [lambda o:o['measures'][0].update(target='Fictional 98%'),lambda o:o['goals'][0].update(area_paths=['foreign/area']),lambda o:o['measures'][0].update(goal_keys=['foreign']),lambda o:o['goals'][0].update(basis_fields=['missing']),lambda o:o['goals'].append(deepcopy(o['goals'][0]))]:
            self.model.bad=bad;before=self.ref()
            with self.assertRaises(ModelUnavailable):self.prepare()
            self.assertEqual(self.ref(),before)
        for p in [dict(goals=[{'id':[]}],measures=[]),dict(goals=[3],measures=[]),dict(goals=[],measures=[dict(id='M-bad',name='Bad',goal_ids=['G-foreign'])])]:
            with self.assertRaises(ValueError):self.save(p)
        self.assertEqual(self.catalog(),{'goals':[],'measures':[]})
    def test_retirement_preserves_previous_publication(self):
        self.apply(self.prepare());self.publish();g=self.catalog()['goals'][0]['id'];old=self.i.latest(g);p=self.payload();p['goals'][0]['active']=False;self.save(p);self.publish()
        self.assertEqual(self.i.latest(g)['body']['status'],'retired');self.assertEqual(self.store.read(old['ref'],{SCOPE}),old)
        for r in Workspace(self.store,'alex').state()['records']:
            if r['kind']=='requirement-drawer':self.assertNotIn(g,[x['id'] for x in r['body'].get('goal_refs',[])])
    def test_requirement_assistant_receives_exact_goal_and_measure_definitions(self):
        self.apply(self.prepare());from test_agent_runtime import RequirementTestModel
        model=RequirementTestModel();w=Workspace(self.store,'priya',model);w.command('requirement-agent-run',dict(expected=self.ref(),drawer='experience/accessibility',skill='draft',consent=True))
        self.assertEqual(model.calls[0]['context']['goals_and_measures'],self.catalog())
    def test_configuration_change_invalidates_proposals_and_tailoring_tracks_linked_goals(self):
        from workbench.requirement_assistant import settings
        from test_scaffold_tailoring import TailorModel
        r=self.prepare();cfg=settings(self.i)
        self.w.requirement_agent.configure(dict(expected=cfg['ref'],draft='Specific revised guidance',review=cfg['config']['review']))
        with self.assertRaises(StaleBasis):self.apply(r)
        self.apply(self.prepare());w=Workspace(self.store,'priya',TailorModel())
        r=w.command('scaffold-tailor',dict(expected=self.ref(),category='experience',consent=True))
        w.command('scaffold-tailor-apply',dict(expected=self.ref(),result=r['ref'],selected=['experience/accessibility','experience/error-recovery'],confirm=True))
        self.assertEqual(w.scaffold_tailoring.state()['stale_areas'],[])
        p=self.payload();p['goals'][0]['outcome']='Changed linked outcome';self.save(p)
        self.assertIn('experience/accessibility',w.scaffold_tailoring.state()['stale_areas'])
        self.assertNotIn('experience/error-recovery',w.scaffold_tailoring.state()['stale_areas'])
    def test_source_checkbox_order_cannot_silently_acknowledge_changed_intake(self):
        self.apply(self.prepare());self.i.save(dict(expected=self.ref(),step='value',value='Changed benefit'))
        p=self.payload();p['goals'][0]['basis_fields'].reverse();self.save(p)
        self.assertIn('value',self.w.goals.state()['goals'][0]['changed_fields'])
    def test_new_connections_cannot_acknowledge_retained_changed_sources(self):
        self.apply(self.prepare());self.i.save(dict(expected=self.ref(),step='value',value='Changed benefit'))
        p=self.payload();p['goals'][0]['basis_fields'].append('need');before=self.ref()
        with self.assertRaises(DecisionBlocked):self.save(p)
        self.assertEqual(self.ref(),before);self.assertIn('value',self.w.goals.state()['goals'][0]['changed_fields'])
        p['goals'][0]['review_basis']=True;self.save(p)
        self.assertEqual(self.w.goals.state()['goals'][0]['changed_fields'],[])
    def test_old_snapshot_cannot_overwrite_newer_goal_edits(self):
        self.apply(self.prepare());before=self.ref();p=self.payload();p['goals'][0]['outcome']='Newer wording';self.save(p)
        with self.assertRaises(StaleBasis):self.w.goals.save(dict(expected=before,**p))
        self.assertEqual(self.catalog()['goals'][0]['body']['outcome'],'Newer wording')
    def test_requirement_review_adopts_new_goal_versions_only_with_human_decision(self):
        self.apply(self.prepare());self.publish();owner=Workspace(self.store,'alex')
        r=owner.create_requirement(dict(title='Resume work',text='Retain entered answers',rationale='Reduce repetition',conditions='Pilot only',drawer='Experience',drawer_id='DRW-experience/accessibility',acceptance_criteria='Resume and inspect saved answers'))
        old=self.i.latest(r['id']);oldgoal=old['body']['goal_refs'][0]
        p=self.payload();p['goals'][0]['outcome']='Revised intended outcome';self.save(p);self.publish()
        selected=[]
        for id,domain in [('CON-research','Research'),('CON-operations','Operations')]:selected.append(asdict(self.store.put(id,'contribution',SCOPE,dict(domain=domain,text='Synthetic finding',source_refs=[]))))
        case=owner.submit_proposal(dict(target=asdict(old['ref']),selected=selected,text='Retain entered answers',acceptance_criteria='Resume and inspect saved answers',conditions='Pilot only',rationale='Reconsidered the goal',changes_intent=False))['id']
        newgoal=self.i.latest(oldgoal['id'])['ref'];self.assertNotEqual(asdict(newgoal),oldgoal);self.assertEqual(self.i.latest(r['id']),old)
        for actor,disposition in [('sam','supported-with-limits'),('maya','cleared-with-conditions')]:Workspace(self.store,actor).review(dict(expected=asdict(owner.loop.case(case)['ref']),disposition=disposition,rationale='Synthetic bounded review'))
        owner.decide(dict(expected=asdict(owner.loop.case(case)['ref']),disposition='approve',rationale='Reviewed exact new basis',confirm=True))
        self.assertEqual(self.i.latest(r['id'])['body']['goal_refs'],[asdict(newgoal)])
        self.assertEqual(self.store.read(old['ref'],{SCOPE}),old)
        self.assertIn(newgoal,self.store.graph({SCOPE}).successors(self.i.latest(r['id'])['ref']))
