from brief_fixture import complete_design_brief
"""Structural packet preparation/release on synthetic data; no data evaluation."""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE, DecisionBlocked
from workbench.intake import Intake, PRIVATE
from workbench.workspace import Workspace
from workbench import packet_preparation
from test_intake import VALUE, CONTEXT


class NoEvaluation:
    def status(self): return dict(configured=False, provider='No evaluation', model='')
    def generate(self, **kwargs): raise AssertionError('Data evaluation is on hold')


class PreflightPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory(); self.path = Path(self.tmp.name)/'packets.sqlite3'
        self.store = Store(self.path)
        self.owner = self.workspace('alex')
        self.owner.setup(dict(title='Synthetic packet proof', intent='Reduce repeated effort', boundary='Preserve user work'))
        req = self.owner.create_requirement(dict(title='Resume task', text='Users can resume the task', rationale='Avoid repetition', drawer='Experience', conditions='Scoped research', acceptance_criteria='Observe resumption'))
        self.req = self.store.latest(req['id'], {SCOPE})

    def tearDown(self): self.store.close(); self.tmp.cleanup()
    def workspace(self, actor): return Workspace(self.store, actor, NoEvaluation())
    def resolved(self, raw, scopes): return self.store.resolve_packet(raw['id'], raw['revision'], scopes)

    def deliverable(self, actor='sam', inputs=None):
        w=self.workspace(actor)
        src=w.command('domain-source', dict(title='Synthetic observation', text='A fictional participant resumed after a pause.'))
        source=self.store.read(Ref(**src['ref']), w.scopes)
        out=w.command('domain-save', dict(title='Synthetic '+actor+' deliverable', deliverable_type=w.domains.profile()['config']['deliverable_types'][0],
            observation='A fictional participant needed a progress cue.', source='Synthetic session 1', limitation='One fictional session; no generalization',
            source_refs=[asdict(source['ref'])], input_refs=inputs or [], links=[dict(ref=asdict(self.req['ref']), relation='refines', rationale='Clarifies resumption')]))
        draft=self.store.latest(out['id'], w.scopes)
        complete_design_brief(w,draft)
        result=w.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='design' if actor=='sam' else 'research', intent_implications='Investigate resumption cues',downstream_needs='Prototype a cue',open_questions='Which cue is useful?'))
        prepared=self.store.latest(result['domainHandoff'], w.scopes)
        return w, source, draft, prepared

    def publish(self, w, draft, prepared, **extra):
        result=w.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(prepared['ref']),confirm=True,**extra))
        contribution=self.store.latest(result['id'], {SCOPE})
        return contribution,self.resolved(result['packet'], {SCOPE})

    def sponsor(self):
        w=self.workspace('priya');i=w.intake;i.start(dict(title='Synthetic sponsor packet'))
        i.save(dict(expected=asdict(i.draft()['ref']),step='value',**VALUE))
        i.accept_value(dict(expected=asdict(i.draft()['ref']),confirm=True,rationale='Review the value hypothesis'))
        i.save(dict(expected=asdict(i.draft()['ref']),step='context',**CONTEXT));i.build(dict(expected=asdict(i.draft()['ref'])))
        w.command('goals-save',dict(expected=asdict(i.draft()['ref']),goals=[dict(id='G-test',title='Reduce repeated effort',outcome='Resume without repetition',active=True,basis_fields=['value'])],
            measures=[dict(id='M-test',name='Resumption rate',goal_ids=['G-test'],active=True,basis_fields=['measures'])]))
        result=w.command('intake-preflight',dict(expected=asdict(i.draft()['ref']),research_focus='Investigate cues',design_focus='Explore resumption',open_questions='No validated baseline'))
        return w,self.store.latest(result['id'], w.scopes)

    def test_research_and_design_prepare_real_private_packets_without_evaluation_or_publication(self):
        for actor, other in [('sam','lee'),('lee','sam')]:
            with self.subTest(actor=actor):
                w,source,draft,prepared=self.deliverable(actor)
                p=self.resolved(prepared['body']['packet'],w.scopes)
                refs={r['ref'] for r in p['records']}
                self.assertTrue({source['ref'],draft['ref'],prepared['ref'],self.req['ref']}<=refs)
                self.assertTrue(any(r['kind']=='intent' for r in p['records']))
                self.assertEqual(p['audience_scopes'],sorted(w.scopes))
                self.assertEqual(next(r for r in p['records'] if r['kind']=='domain-handoff')['body']['handoff']['open_questions'],'Which cue is useful?')
                self.assertFalse(any(r['kind']=='contribution' for r in self.workspace(other).state()['records']))
                self.assertIn(p,self.workspace(actor).state()['packets'])
                for outsider in (other,'alex','priya','maya'):
                    self.assertNotIn(p['id'],[p['id'] for p in self.workspace(outsider).state()['packets']])
                    with self.assertRaises(PermissionError):self.resolved(prepared['body']['packet'],self.workspace(outsider).scopes)
                same=w.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient=prepared['body']['recipient'],**prepared['body']['handoff']))
                self.assertEqual(same['domainHandoff'],prepared['ref'].id)
                self.assertIsNotNone(self.owner.packet_for(self.req['ref']))

    def test_domain_release_uses_only_the_prepared_selection_and_records_exact_reference_mapping(self):
        w,source,draft,prepared=self.deliverable()
        original=self.resolved(prepared['body']['packet'],w.scopes)
        unrelated=self.store.put('UNSELECTED','source',SCOPE,dict(text='Must not enter this packet'))
        count=self.store.db.execute('SELECT COUNT(*) FROM packets').fetchone()[0]
        with self.assertRaises(PermissionError):self.publish(w,draft,prepared)
        self.assertEqual(self.store.db.execute('SELECT COUNT(*) FROM packets').fetchone()[0],count)
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='packet-release'").fetchone())
        shared,packet=self.publish(w,draft,prepared,release_sources=True)
        receipt=next(r for r in packet['records'] if r['kind']=='packet-release')
        mapping={Ref(**m['prepared']):Ref(**m['released']) for m in receipt['body']['reference_map']}
        self.assertEqual(set(mapping),{Ref(**raw) for raw in original['refs']})
        self.assertEqual(mapping[draft['ref']],shared['ref']);self.assertEqual(mapping[prepared['ref']],shared['ref'])
        self.assertNotEqual(mapping[source['ref']],source['ref'])
        self.assertEqual(self.store.read(mapping[source['ref']],{SCOPE})['body']['text'],source['body']['text'])
        self.assertEqual({Ref(**r) for r in packet['refs']},set(mapping.values())|{receipt['ref']})
        self.assertNotIn(unrelated,mapping.values())
        self.assertTrue(all(r['scope']==SCOPE for r in packet['records']))
        self.assertEqual(self.resolved(prepared['body']['packet'],w.scopes),original)
        self.assertEqual(self.req,self.store.latest(self.req['ref'].id,{SCOPE}))
        with self.assertRaises(DecisionBlocked):self.publish(w,draft,prepared,release_sources=True)

    def test_selected_research_inputs_and_linked_goal_versions_are_preserved_in_design_packet(self):
        research=self.deliverable();shared,_=self.publish(*[research[n] for n in (0,2,3)],release_sources=True)
        goal=self.store.put('G-shared','goal',SCOPE,dict(title='Resume confidently',outcome='Resume work',measure_refs=[]))
        measure=self.store.put('M-shared','success-measure',SCOPE,dict(name='Resumption rate'))
        b=deepcopy(self.req['body']);b.update(goal_refs=[asdict(goal)],measure_refs=[asdict(measure)])
        self.req=self.store.read(self.store.put(self.req['ref'].id,'requirement',SCOPE,b,self.req['ref'].revision),{SCOPE})
        w,source,draft,prepared=self.deliverable('lee',[asdict(shared['ref'])])
        p=self.resolved(prepared['body']['packet'],w.scopes)
        self.assertTrue({shared['ref'],goal,measure}<={r['ref'] for r in p['records']})
        _,released=self.publish(w,draft,prepared,release_sources=True)
        self.assertTrue({shared['ref'],goal,measure}<={r['ref'] for r in released['records']})

    def test_stale_evidence_rejects_release_but_packet_inspection_keeps_old_content(self):
        w,source,draft,prepared=self.deliverable()
        newer=self.store.put(source['ref'].id,source['kind'],source['scope'],{**source['body'],'text':'Changed fictional finding'},source['ref'].revision)
        with self.assertRaises(StaleBasis):self.publish(w,draft,prepared,release_sources=True)
        p=self.resolved(prepared['body']['packet'],w.scopes)
        self.assertIn(source,p['records'])
        self.assertIn(dict(previous=asdict(source['ref']),current=asdict(newer)),p['changed_refs'])
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='packet-release'").fetchone())

    def test_sponsor_packet_contains_draft_goals_and_releases_them_as_unapproved_proposals(self):
        w,prepared=self.sponsor();i=w.intake
        p=self.resolved(prepared['body']['packet'],w.scopes)
        self.assertTrue({'sponsor-preflight','goal-draft','success-measure-draft'}<={r['kind'] for r in p['records']})
        self.assertEqual(i.cases(),[])
        for actor in ('sam','lee','alex'):
            self.assertNotIn(p['id'],[p['id'] for p in self.workspace(actor).state()['packets']])
        result=w.command('intake-request',dict(expected=asdict(i.draft()['ref']),preflight=asdict(prepared['ref']),confirm=True))
        case=i.latest(result['id']);published=self.resolved(case['body']['packet'],{SCOPE})
        self.assertTrue({'intake-case','goal-proposal','success-measure-proposal','packet-release'}<={r['kind'] for r in published['records']})
        receipt=next(r for r in published['records'] if r['kind']=='packet-release')
        self.assertEqual({Ref(**r) for r in p['refs']},{Ref(**m['prepared']) for m in receipt['body']['reference_map']})
        for r in published['records']:
            if r['kind'].endswith('-proposal'):self.assertEqual(r['body']['status'],'proposed-for-direction-review')
        self.assertEqual(case['body']['status'],'pending-review')
        self.assertEqual(self.resolved(prepared['body']['packet'],w.scopes),p)
        # The pre-existing baseline cannot change until separate sponsor governance.
        self.assertEqual(i.latest('INT-001')['body']['text'],'Reduce repeated effort')
        self.assertTrue(all(r['scope']==SCOPE for r in published['records']))

    def test_prepared_packet_survives_reopening_and_does_not_leak_through_listing(self):
        w,source,draft,prepared=self.deliverable()
        p=self.resolved(prepared['body']['packet'],w.scopes)
        self.store.close();self.store=Store(self.path)
        self.assertEqual(self.resolved(prepared['body']['packet'],self.workspace('sam').scopes),p)
        self.assertNotIn(p['id'],[p['id'] for p in self.store.packet_manifests({SCOPE})])
        private=prepared['body']['packet']
        with self.assertRaises(PermissionError):self.store.read_packet(private['id'],private['revision'],{SCOPE})

    def test_release_cannot_replace_shared_context_with_a_newer_unreviewed_version(self):
        w,source,draft,prepared=self.deliverable()
        p=self.resolved(prepared['body']['packet'],w.scopes)
        newer=self.store.put(self.req['ref'].id,'requirement',SCOPE,self.req['body'],self.req['ref'].revision)
        with self.assertRaises(ValueError):
            packet_preparation.release(self.store,p,'INVALID',1,{self.req['ref']:newer},'sam')
        self.assertFalse(self.store.db.execute("SELECT 1 FROM records WHERE kind='packet-release'").fetchone())

    def test_old_preflights_require_fresh_packet_preparation_without_rewriting_history(self):
        w,source,draft,prepared=self.deliverable()
        b=deepcopy(prepared['body']);b.pop('packet')
        old=self.store.put('OLD-HANDOFF','domain-handoff',prepared['scope'],b)
        with self.assertRaises(StaleBasis):w.domains.checked_handoff(asdict(old))
        self.assertNotIn('packet',self.store.read(old,w.scopes)['body'])

    def test_release_revision_does_not_collide_with_a_packet_created_by_a_requirement_decision(self):
        w,source,draft,prepared=self.deliverable()
        shared,first=self.publish(w,draft,prepared,release_sources=True)
        self.store.packet(first['id'],2,'Synthetic intervening decision',[Ref(**r) for r in first['refs']],{SCOPE},{SCOPE})
        edited=w.command('domain-save',{**draft['body'],'expected':asdict(draft['ref']),'interpretation':'Revised fictional interpretation'})
        draft=self.store.latest(edited['id'],w.scopes)
        out=w.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='design',open_questions='A new question'))
        prepared=self.store.latest(out['domainHandoff'],w.scopes)
        newer,packet=self.publish(w,draft,prepared,release_sources=True)
        self.assertEqual(newer['ref'].revision,2)
        self.assertEqual(packet['revision'],3)
        self.assertEqual(newer['body']['packet'],dict(id=packet['id'],revision=3))
        self.assertEqual(self.resolved(dict(id=first['id'],revision=1),{SCOPE})['records'],first['records'])
