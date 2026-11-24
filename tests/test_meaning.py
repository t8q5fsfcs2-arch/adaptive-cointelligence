from pathlib import Path
import tempfile, unittest

from workbench.core import Store, StaleBasis
from workbench.decisions import SCOPE
from workbench.domain_knowledge import entry, snapshot
from workbench.workspace import Workspace


class MeaningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.store = Store(Path(self.temp.name) / 'db')
        Workspace(self.store, 'alex').setup(dict(title='Fictional meaning', intent='Reduce missed visits', boundary='Synthetic'))
        self.sam = Workspace(self.store, 'sam'); self.lee = Workspace(self.store, 'lee'); self.priya = Workspace(self.store, 'priya')
        self.r = entry('term', 'Missed appointment', 'Did not attend and did not cancel.', 'Fictional.')
        self.d = entry('term', 'No-show', 'Did not attend, including late cancellations.', 'Fictional.')
        self.rule = entry('standard', 'Rule', 'A fictional rule.', 'Fictional.')
        self.save(self.sam, 'research', [self.r, self.rule]); self.save(self.lee, 'design', [self.d])
    def tearDown(self): self.store.close(); self.temp.cleanup()
    def save(self, w, key, entries):
        w.command('domain-knowledge-save', dict(domain=key, expected=snapshot(self.store, key)['ref'], entries=entries, reason='Fictional.', confirm_active=True))
    def mapping(self, w=None, **extra):
        data = dict(type='mapping', relation='distinct-from', reason='They count late cancellations differently.',
                    **{'from': dict(domain='research', id=self.r['id']), 'to': dict(domain='design', id=self.d['id'])}); data.update(extra)
        return (w or self.sam).command('meaning-propose', data)['ref']
    def decide(self, w, ref, outcome='approve', **extra):
        data = dict(proposal=ref, outcome=outcome, reason='Fictional review.', confirm=True); data.update(extra)
        return w.command('meaning-decide', data)['ref']
    def item(self, w=None): return (w or self.sam).state()['meaning']['items'][0]

    def test_a_mapping_takes_effect_only_when_both_team_leads_explicitly_approve(self):
        ref = self.mapping()
        self.assertEqual(self.item()['status'], 'proposed'); self.assertEqual(self.item(self.lee)['mine'], ['design']); self.assertEqual(self.sam.state()['meaning']['waiting_on_me'], 1)
        with self.assertRaises(ValueError): self.decide(self.sam, ref, confirm=False)
        with self.assertRaises(PermissionError): self.decide(self.priya, ref, actor='sam')
        ref = self.decide(self.sam, ref); self.assertEqual(self.item()['status'], 'proposed'); self.assertEqual(self.item()['waiting'], ['design'])
        with self.assertRaises(PermissionError): self.decide(self.sam, ref)
        self.decide(self.lee, ref); item = self.item()
        self.assertEqual(item['status'], 'approved'); self.assertEqual(set(item['decisions']), {'research', 'design'})
        self.assertEqual(snapshot(self.store, 'research')['entries'], [self.r, self.rule])  # team knowledge itself is not rewritten

    def test_one_decline_closes_it_and_the_record_is_kept(self):
        ref = self.mapping(); self.decide(self.lee, ref, 'decline')
        item = self.item(); self.assertEqual(item['status'], 'declined'); self.assertEqual(item['decisions']['design']['outcome'], 'decline')
        with self.assertRaises((ValueError, StaleBasis)): self.decide(self.sam, item['ref'])

    def test_mappings_join_current_concepts_of_two_different_teams_with_a_known_relation(self):
        for bad in (dict(relation='equals'), dict(reason=' '), {'to': dict(domain='research', id=self.r['id'])},
                    {'from': dict(domain='research', id=self.rule['id'])}, {'to': dict(domain='design', id='KN-000000000000')}):
            with self.assertRaises(ValueError): self.mapping(**bad)
        with self.assertRaises(PermissionError): self.mapping(self.priya)
        self.mapping()
        with self.assertRaises(ValueError): self.mapping(self.lee)  # no duplicate while open

    def test_a_concept_changed_since_the_proposal_cannot_be_approved_on_the_old_basis(self):
        ref = self.mapping()
        self.save(self.lee, 'design', [dict(self.d, definition='Did not attend and gave no notice.')])
        self.assertEqual(self.item()['changed'], ['No-show'])
        with self.assertRaises(StaleBasis): self.decide(self.sam, ref)
        self.decide(self.sam, ref, 'decline'); self.assertEqual(self.item()['status'], 'declined')

    def test_sharing_a_concept_is_decided_by_its_own_team_lead_alone(self):
        ref = self.lee.command('meaning-propose', dict(type='share', grantee='design', reason='Design uses this term in flows.', **{'from': dict(domain='research', id=self.r['id'])}))['ref']
        with self.assertRaises(PermissionError): self.decide(self.lee, ref)
        self.decide(self.sam, ref); item = self.item(self.lee)
        self.assertEqual((item['status'], item['grantee'], item['deciders']), ('approved', 'design', ['research']))
        with self.assertRaises(ValueError): self.sam.command('meaning-propose', dict(type='share', grantee='research', reason='x', **{'from': dict(domain='research', id=self.r['id'])}))

    def test_the_proposer_withdraws_an_open_proposal_and_a_lead_retires_an_approved_one(self):
        ref = self.mapping()
        with self.assertRaises(PermissionError): self.lee.command('meaning-close', dict(proposal=ref, reason='Not mine.'))
        self.sam.command('meaning-close', dict(proposal=ref, reason='Wrong relation.')); self.assertEqual(self.item()['status'], 'withdrawn')
        ref = self.mapping(relation='related'); ref = self.decide(self.sam, ref); ref = self.decide(self.lee, ref)
        with self.assertRaises(PermissionError): self.priya.command('meaning-close', dict(proposal=ref, reason='No.'))
        self.lee.command('meaning-close', dict(proposal=ref, reason='Design changed its term.'))
        item = self.item(); self.assertEqual(item['status'], 'retired'); self.assertEqual(item['ref']['revision'], 4)
        self.assertEqual(self.store.read(type(self.store.latest(item['ref']['id'], {SCOPE})['ref'])(item['ref']['id'], 3), {SCOPE})['body']['status'], 'approved')

    def test_a_stale_view_cannot_act(self):
        ref = self.mapping(); self.decide(self.sam, ref)
        with self.assertRaises(StaleBasis): self.decide(self.lee, ref)


if __name__ == '__main__': unittest.main()
