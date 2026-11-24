from pathlib import Path
import tempfile, unittest

from workbench.core import Store, StaleBasis
from workbench.domain_knowledge import entry, snapshot
from workbench.enterprise import Enterprise, curation
from workbench.projects import Projects
from workbench.workspace import Workspace


class EnterpriseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); anchor = Path(self.temp.name) / 'site.sqlite3'
        Store(anchor).close(); self.projects = Projects(anchor)
        self.pid = self.projects.create(dict(title='Fictional enterprise project'), 'priya')['project_id']
        with self.projects.db() as db: self.path = db.execute('SELECT path FROM projects WHERE id=?', (self.pid,)).fetchone()[0]
        self.term = dict(entry('term', 'Visit', 'A booked time when a patient is expected.', 'Fictional.'), includes='Confirmed bookings.', excludes='Walk-ins.', not_confused_with='', reach='domain')
        self.plain = entry('term', 'Slot', 'An open time.', 'Fictional.')
        self.save([self.term, self.plain])
        self.e = Enterprise(anchor, self.projects); self.mine = {self.pid}
        self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=['alex'], stewards=['priya']), reason='Fictional assignment.', expected=None))
    def tearDown(self): self.temp.cleanup()
    def save(self, entries):
        store = Store(self.path)
        try: Workspace(store, 'sam').command('domain-knowledge-save', dict(domain='research', expected=snapshot(store, 'research')['ref'], entries=entries, reason='Fictional.', confirm_active=True))
        finally: store.close()
    def propose(self, actor='alex', **extra):
        data = dict(origin=dict(project=self.pid, domain='research', entry=self.term['id']), reach='enterprise', reason='Every clinic uses this word.'); data.update(extra)
        return self.e.propose(actor, self.mine, data)['ref']
    def decide(self, actor, ref, outcome='approve', **extra):
        data = dict(ref=ref, outcome=outcome, reason='Fictional review.', confirm=True); data.update(extra)
        return self.e.decide(actor, self.mine, data)['ref']
    def state(self, actor='administrator', admin=True): return self.e.state(actor, admin, self.mine)

    def test_roles_are_assigned_by_an_administrator_and_nobody_proposes_and_decides(self):
        ref = self.state()['roles']['ref']
        with self.assertRaises(PermissionError): self.e.save_roles('sam', False, dict(roles=dict(semantic_services=[], stewards=['sam']), reason='x', expected=ref))
        with self.assertRaises(ValueError): self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=['alex'], stewards=['alex']), reason='x', expected=ref))
        with self.assertRaises(ValueError): self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=['nobody'], stewards=[]), reason='x', expected=ref))
        with self.assertRaises(StaleBasis): self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=[], stewards=[]), reason='x', expected=None))
        self.assertEqual(self.state('alex', False)['roles_mine'], ['semantic_services']); self.assertFalse(self.state('lee', False)['can_view'])
        self.assertNotIn('overview', self.state('lee', False))

    def test_wider_reach_needs_the_team_lead_and_a_steward_as_two_people_and_copies_the_exact_wording(self):
        ref = self.propose()
        with self.assertRaises(PermissionError): self.decide('alex', ref)          # semantic services never decides
        with self.assertRaises(PermissionError): self.decide('lee', ref)           # not this team's lead, not a steward
        with self.assertRaises(ValueError): self.decide('sam', ref, confirm=False)
        ref = self.decide('sam', ref); self.assertEqual(self.state()['concepts'], [])
        self.assertEqual(self.state('priya', False)['proposals'][0]['mine'], ['steward'])
        self.decide('priya', ref); s = self.state()
        concept = s['concepts'][0]
        self.assertEqual((concept['title'], concept['reach'], concept['includes'], concept['status']), ('Visit', 'enterprise', 'Confirmed bookings.', 'active'))
        self.assertEqual(concept['approved'], dict(lead='sam', steward='priya')); self.assertEqual(concept['origin']['entry'], self.term['id'])
        self.assertEqual(s['proposals'][0]['status'], 'approved'); self.assertEqual(s['overview']['reach']['enterprise'], 1)
        store = Store(self.path)
        try: self.assertEqual(snapshot(store, 'research')['entries'][0]['reach'], 'domain')   # the project store is never written from above
        finally: store.close()

    def test_one_person_cannot_approve_alone_even_holding_both_capacities(self):
        self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=['alex'], stewards=['sam']), reason='x', expected=self.state()['roles']['ref']))
        ref = self.propose(); ref = self.decide('sam', ref)
        self.assertEqual(self.state('sam', False)['proposals'][0]['mine'], [])
        with self.assertRaises(PermissionError): self.decide('sam', ref)

    def test_proposing_needs_the_role_or_the_lead_project_access_and_a_current_active_concept(self):
        with self.assertRaises(PermissionError): self.propose('lee')
        with self.assertRaises(PermissionError): self.e.propose('alex', set(), dict(origin=dict(project=self.pid, domain='research', entry=self.term['id']), reach='enterprise', reason='x'))
        for bad in (dict(reach='domain'), dict(reach='named-domains'), dict(reason=' '), dict(origin=dict(project=self.pid, domain='research', entry='KN-000000000000'))):
            with self.assertRaises(ValueError): self.propose(**bad)
        self.propose('sam', reach='named-domains', named=['Clinical access'])
        with self.assertRaises(ValueError): self.propose()

    def test_a_concept_changed_after_the_proposal_cannot_be_approved(self):
        ref = self.propose(); self.save([dict(self.term, excludes='Walk-ins and waitlist holds.'), self.plain])
        self.assertTrue(self.state()['proposals'][0]['changed'])
        with self.assertRaises(StaleBasis): self.decide('sam', ref)
        self.decide('sam', ref, 'decline'); self.assertEqual(self.state()['proposals'][0]['status'], 'declined')

    def test_withdraw_retire_and_a_later_approval_keep_every_version(self):
        ref = self.propose()
        with self.assertRaises(PermissionError): self.e.close('sam', dict(ref=ref, reason='x'))
        self.e.close('alex', dict(ref=ref, reason='Too early.'))
        ref = self.decide('priya', self.decide('sam', self.propose())); cref = self.state()['concepts'][0]['ref']
        with self.assertRaises(PermissionError): self.e.close('sam', dict(ref=cref, reason='x'))
        self.e.close('priya', dict(ref=cref, reason='Superseded.'))
        s = self.state(); self.assertEqual(s['concepts'][0]['status'], 'retired'); self.assertEqual(s['overview']['reach']['enterprise'], 0)
        self.decide('priya', self.decide('sam', self.propose()))
        again = self.state()['concepts']; self.assertEqual(len(again), 1); self.assertEqual((again[0]['status'], again[0]['ref']['revision']), ('active', 3))

    def test_a_session_groups_live_proposals_and_topics_and_its_facilitator_never_decides(self):
        with self.assertRaises(PermissionError): self.e.create_session('sam', self.mine, dict(title='x', project=self.pid, domain='research'))
        with self.assertRaises(PermissionError): self.e.create_session('alex', set(), dict(title='x', project=self.pid, domain='research'))
        ref = self.e.create_session('alex', self.mine, dict(title='Research meaning alignment', when='Nov 24', project=self.pid, domain='research'))['ref']
        pref = self.propose()
        view = self.state('alex', False)['sessions'][0]; self.assertEqual([l['type'] for l in view['linkable']], ['reach']); self.assertTrue(view['can_edit'])
        items = [dict(title='Scope of the glossary', note=''), dict(title='Reach of Visit', note='', link=dict(type='reach', id=pref['id']))]
        with self.assertRaises(PermissionError): self.e.save_session('sam', dict(ref=ref, items=items))
        with self.assertRaises(ValueError): self.e.save_session('alex', dict(ref=ref, items=[dict(title='Bad', note='', link=dict(type='reach', id='EPROPOSAL-000000000000'))]))
        with self.assertRaises(ValueError): self.e.save_session('alex', dict(ref=ref, items=items + [items[1]]))
        ref = self.e.save_session('alex', dict(ref=ref, items=items))['ref']
        view = self.state('alex', False)['sessions'][0]
        self.assertEqual([i['state'] for i in view['items']], ['topic', 'open']); self.assertEqual(view['items'][1]['waiting'], ['lead', 'steward']); self.assertEqual(view['agreed'], 0)
        # marking a linked item "discussed" is ignored: only the deciders move it
        saved = [dict(view['items'][0], discussed=True), dict(view['items'][1], discussed=True)]
        ref = self.e.save_session('alex', dict(ref=ref, items=saved))['ref']
        self.assertEqual([i['state'] for i in self.state('alex', False)['sessions'][0]['items']], ['discussed', 'open'])
        self.decide('priya', self.decide('sam', pref))
        view = self.state('alex', False)['sessions'][0]; self.assertEqual([i['state'] for i in view['items']], ['discussed', 'agreed']); self.assertEqual(view['agreed'], 2)
        with self.assertRaises(ValueError): self.e.close_session('alex', dict(ref=ref, summary=' '))
        self.e.close_session('alex', dict(ref=ref, summary='Visit agreed for the enterprise.'))
        closed = self.state('alex', False)['sessions'][0]; self.assertEqual((closed['status'], closed['can_edit'], closed['ref']['revision']), ('closed', False, 4))
        with self.assertRaises(ValueError): self.e.save_session('alex', dict(ref=closed['ref'], items=[]))
        self.assertEqual(self.e.state('lee', False, set())['sessions'], [])   # not a member, no role

    def test_the_overview_counts_without_exposing_wording_and_non_members_see_no_foreign_proposals(self):
        self.propose(); o = self.state()['overview']; row = next(r for r in o['domains'] if r['domain'] == 'research')
        self.assertEqual((row['concepts'], row['bounded'], row['curation'], row['waiting']), (2, 1, 'moderate', 1))
        self.assertNotIn('A booked time', str(o)); self.assertEqual(o['totals']['concepts'], 2)
        self.assertEqual(self.e.state('lee', False, set())['proposals'], [])
        self.assertEqual([curation(0, 0), curation(3, 0), curation(3, 2), curation(3, 3)], ['empty', 'low', 'moderate', 'high'])


if __name__ == '__main__': unittest.main()
