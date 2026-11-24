from pathlib import Path
import tempfile, unittest

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.domain_knowledge import entry, snapshot
from workbench.enterprise import Enterprise
from workbench.projects import Projects
from workbench.workspace import Workspace


class AdoptionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); anchor = Path(self.temp.name) / 'site.sqlite3'
        Store(anchor).close(); self.projects = Projects(anchor)
        self.pid = self.projects.create(dict(title='Fictional adoption project'), 'priya')['project_id']
        with self.projects.db() as db: self.path = db.execute('SELECT path FROM projects WHERE id=?', (self.pid,)).fetchone()[0]
        self.term = dict(entry('term', 'Visit', 'A booked time.', 'Fictional.'), includes='Confirmed bookings.', excludes='', not_confused_with='', reach='domain')
        self.store = Store(self.path); self.sam = Workspace(self.store, 'sam'); self.lee = Workspace(self.store, 'lee')
        self.sam.command('domain-knowledge-save', dict(domain='research', expected=None, entries=[self.term], reason='Fictional.', confirm_active=True))
        self.e = Enterprise(anchor, self.projects)
        self.e.save_roles('administrator', True, dict(roles=dict(semantic_services=['alex'], stewards=['priya']), reason='x', expected=None))
        self.promote()
    def tearDown(self): self.store.close(); self.temp.cleanup()
    def promote(self, **extra):
        ref = self.e.propose('alex', {self.pid}, dict(origin=dict(project=self.pid, domain='research', entry=self.term['id']), reach='enterprise', reason='x', **extra))['ref']
        for who in ('sam', 'priya'): ref = self.e.decide(who, {self.pid}, dict(ref=ref, outcome='approve', reason='x', confirm=True))['ref']
        self.cref = next(c['ref'] for c in self.e.state('administrator', True, {self.pid})['concepts'])
    def adopt(self, w=None, domain='design', ref=None, project='another-project', **extra):
        w = w or self.lee
        current = next((i['ref'] for i in w.state()['adoptions']['items'] if i['domain'] == domain), None)
        data = dict(domain=domain, reason='Design uses this word in flows.', confirm=True, expected=current,
                    _enterprise=self.e.current_concept(ref or self.cref), _project=project); data.update(extra)
        return w.command('enterprise-adopt', data)

    def test_a_team_lead_adopts_an_exact_version_with_its_full_wording(self):
        with self.assertRaises(PermissionError): self.adopt(self.sam)
        with self.assertRaises(ValueError): self.adopt(confirm=False)
        with self.assertRaises(ValueError): self.adopt(_enterprise=None)
        self.adopt(); item = self.lee.state()['adoptions']['items'][0]
        self.assertEqual((item['concept'], item['wording']['title'], item['wording']['includes'], item['status']), (self.cref, 'Visit', 'Confirmed bookings.', 'adopted'))
        with self.assertRaises(ValueError): self.adopt()   # same version again
        used = self.e.state('administrator', True, {self.pid})['concepts'][0]['used_by']
        self.assertEqual(used, [dict(project_title='Fictional adoption project', team='Design', revision=1)])

    def test_a_newer_enterprise_version_never_changes_the_project_until_the_lead_moves_it(self):
        self.adopt(); old = self.cref
        self.sam.command('domain-knowledge-save', dict(domain='research', expected=snapshot(self.store, 'research')['ref'], entries=[dict(self.term, excludes='Walk-ins.')], reason='x', confirm_active=True))
        self.promote(); self.assertEqual(self.cref['revision'], 2)
        item = self.lee.state()['adoptions']['items'][0]; self.assertEqual((item['concept'], item['wording']['excludes']), (old, ''))
        with self.assertRaises(StaleBasis): self.e.current_concept(old)   # the old version cannot be adopted afresh
        self.adopt(); item = self.lee.state()['adoptions']['items'][0]
        self.assertEqual((item['concept']['revision'], item['wording']['excludes'], item['ref']['revision']), (2, 'Walk-ins.', 2))
        self.assertEqual(self.store.read(type(self.store.latest(item['ref']['id'], {SCOPE})['ref'])(item['ref']['id'], 1), {SCOPE})['body']['wording']['excludes'], '')

    def test_named_reach_own_concept_and_drop(self):
        with self.assertRaises(ValueError): self.adopt(self.sam, domain='research', project=self.pid)   # the owning team does not adopt its own concept
        self.adopt(); item = self.lee.state()['adoptions']['items'][0]
        with self.assertRaises(PermissionError): self.sam.command('enterprise-adoption-drop', dict(adoption=item['ref'], reason='x'))
        self.lee.command('enterprise-adoption-drop', dict(adoption=item['ref'], reason='No longer used.'))
        self.assertEqual(self.lee.state()['adoptions']['items'][0]['status'], 'dropped')
        self.assertEqual(self.e.state('administrator', True, {self.pid})['concepts'][0]['used_by'], [])
        concept = dict(self.e.current_concept(self.cref), reach='named-domains', named=['Clinical access'])
        with self.assertRaises(PermissionError): self.adopt(_enterprise=concept)
        self.adopt(_enterprise=dict(concept, named=['design']))

    def test_the_server_resolves_the_concept_and_discards_anything_the_browser_sends(self):
        source = (Path(__file__).parent.parent / 'src/workbench/web.py').read_text()
        strip = source.index("data.pop('_enterprise', None); data.pop('_project', None)"); resolve = source.index("data['_enterprise'] = self.server.enterprise.current_concept(data.get('concept'))")
        self.assertLess(strip, resolve); self.assertLess(resolve, source.index('result = workspace.command(action, data)'))
        with self.assertRaises(ValueError): self.e.current_concept(dict(id='ECONCEPT-000000000000', revision=1))


if __name__ == '__main__': unittest.main()
