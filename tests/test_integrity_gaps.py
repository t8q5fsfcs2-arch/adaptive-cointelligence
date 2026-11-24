"""Synthetic persistence/permissions tests, not a semantic or human simulation."""
from copy import deepcopy
from dataclasses import asdict
import unittest

from workbench.core import Store, Ref, StaleBasis
from workbench.decisions import SCOPE
from workbench.workspace import Workspace


def seed(store, scope='domain:research'):
    store.put('SRC', 'source', scope, dict(title='Synthetic transition rule', text='A note is required before resolution.'))
    source = dict(meaning='A note is required before resolution.', quote='requires a note', full_clause='Resolution requires a note.')
    gaps = [dict(key='G1', packet_ref='PKT:v1', obligation_ref='C1', part_ref='C1/P1/K1',
                 status='uncertain', remaining_gap='Supply the transition rule.', source=source)]
    parts = [dict(part_ref='C1/P1/K1', reasoning='Notification alone does not establish the prerequisite.',
                  interpretation=dict(state='settled', reading='Require the note before resolution.'), evidence_quotes=[])]
    body = dict(context=dict(review_basis=dict(purpose='historical', boundary='Not eligible for current approval.')),
                decision_trace=dict(evidence_level='documentary-alignment', mapping_groups=[],
                    recommendation=dict(unresolved_material_gaps=gaps),
                    packet_findings=[dict(packet_ref='PKT:v1', parts=parts)]))
    return store.put('ASSESSMENT', 'integrity-assessment', scope, body)


class GapTests(unittest.TestCase):
    def setUp(self):
        self.store=Store(':memory:'); self.ref=seed(self.store)
        self.w=Workspace(self.store, 'sam', principal_id='account-sam')
        self.original=deepcopy(self.store.read(self.ref, self.w.scopes))
        self.card=self.w.integrity_gaps.state()[0]

    def tearDown(self): self.store.close()

    def payload(self, **kwargs):
        return dict(assessment=asdict(self.ref), key=self.card['key'], expected=None,
                    request_id='request-one', kind='clarification', note='Synthetic contributor explanation.', **kwargs)

    def count(self): return self.store.db.execute('SELECT COUNT(*) FROM records').fetchone()[0]

    def test_read_is_projection_without_writes_and_keeps_reference(self):
        before=self.count(); c=self.w.command('integrity-gap-read', self.card)
        self.assertEqual(self.count(),before); self.assertEqual(c['assessment'],asdict(self.ref))
        self.assertEqual(c['occurrences'][0]['part_ref'],'C1/P1/K1')
        self.assertEqual(c['purpose'],'historical'); self.assertNotIn('fields',c['sources'][0])
        source=self.w.command('integrity-gap-source-read',dict(self.card,source=dict(id='SRC',revision=1)))
        self.assertIn('required before',source['fields']['text'])

    def test_clarification_persists_with_server_identity_and_no_ratification(self):
        p=self.payload(actor='alex',principal='spoof'); out=self.w.command('integrity-gap-respond',p)
        r=self.store.read(Ref(**out['ref']),self.w.scopes)
        self.assertEqual(r['body']['actor'],'sam');self.assertEqual(r['body']['principal'],'account-sam')
        self.assertEqual(r['body']['status'],'awaiting-review')
        fresh=Workspace(self.store,'sam').command('integrity-gap-read',self.card)
        self.assertEqual(len(fresh['responses']),1);self.assertEqual(fresh['expected']['revision'],1)
        self.assertEqual(self.store.read(self.ref,self.w.scopes),self.original)
        self.assertEqual(self.w.integrity_gaps.state()[0]['collection_status'],'information-supplied')
        self.assertEqual(self.w.integrity_gaps.state()[0]['status'],'uncertain')

    def test_exact_evidence_is_pinned_and_has_dependency(self):
        p=self.payload();p.update(kind='evidence',evidence=dict(ref=dict(id='SRC',revision=1),field='text',quote='A note is required'))
        out=self.w.command('integrity-gap-respond',p);r=self.store.read(Ref(**out['ref']),self.w.scopes)
        self.assertEqual(r['body']['evidence']['ref'],dict(id='SRC',revision=1))
        self.assertTrue(self.store.graph(self.w.scopes).has_edge(Ref(**out['ref']),Ref('SRC',1)))

    def test_new_source_requires_provenance_and_is_explicitly_unverified(self):
        p=self.payload();p.update(kind='evidence',evidence=dict(title='Synthetic policy',text='Resolution requires a note.',source_locator='Fictional policy v1, section 3'))
        out=self.w.command('integrity-gap-respond',p);r=self.store.read(Ref(**out['ref']),self.w.scopes)
        source=self.store.read(Ref(**r['body']['evidence']['ref']),self.w.scopes)
        self.assertEqual(source['body']['status'],'human-supplied-unverified')
        self.assertEqual(source['scope'],'domain:research');self.assertEqual(self.count(),5)

    def test_invalid_quote_and_missing_origin_write_nothing(self):
        for evidence in [dict(ref=dict(id='SRC',revision=1),field='text',quote='Invented quote'),dict(title='X',text='Y')]:
            p=self.payload();p.update(kind='evidence',evidence=evidence)
            with self.assertRaises(ValueError):self.w.command('integrity-gap-respond',p)
            self.assertEqual(self.count(),2)

    def test_exact_retry_is_idempotent_but_changed_retry_fails(self):
        p=self.payload();a=self.w.command('integrity-gap-respond',p);b=self.w.command('integrity-gap-respond',p)
        self.assertEqual(a,b);self.assertEqual(self.count(),4)
        with self.assertRaises(ValueError):self.w.command('integrity-gap-respond',dict(p,note='Different'))

    def test_parallel_stale_save_rejected_then_fresh_append_retains_both(self):
        self.w.command('integrity-gap-respond',self.payload());p=dict(self.payload(),request_id='second')
        with self.assertRaises(StaleBasis):self.w.command('integrity-gap-respond',p)
        p['expected']=self.w.command('integrity-gap-read',self.card)['expected'];self.w.command('integrity-gap-respond',p)
        self.assertEqual(len(self.w.command('integrity-gap-read',self.card)['responses']),2)

    def test_new_source_revision_requires_reselection(self):
        self.store.put('SRC','source','domain:research',dict(title='New',text='Changed wording'),expected_revision=1)
        p=self.payload();p.update(kind='evidence',evidence=dict(ref=dict(id='SRC',revision=1),field='text',quote='A note'))
        with self.assertRaises(StaleBasis):self.w.command('integrity-gap-respond',p)
        self.assertEqual(self.count(),3)

    def test_private_review_not_disclosed_to_other_role(self):
        other=Workspace(self.store,'lee');self.assertEqual(other.integrity_gaps.state(),[])
        for action in ('integrity-gap-read','integrity-gap-respond'):
            with self.assertRaises(PermissionError):other.command(action,self.payload())

    def test_private_source_cannot_be_copied_to_shared_gap(self):
        self.store.put('SHARED','integrity-assessment',SCOPE,self.original['body'])
        c=next(c for c in self.w.integrity_gaps.state() if c['assessment']['id']=='SHARED')
        p=dict(self.payload(),assessment=c['assessment'],key=c['key'],kind='evidence',
               evidence=dict(ref=dict(id='SRC',revision=1),field='text',quote='A note'))
        with self.assertRaises(PermissionError):self.w.command('integrity-gap-respond',p)
        with self.assertRaises(PermissionError):self.w.command('integrity-gap-source-read',dict(c,source=dict(id='SRC',revision=1)))
        self.assertEqual(self.count(),3)

    def test_revoked_member_cannot_respond(self):
        w=Workspace(self.store,'sam',decision_members=[])
        with self.assertRaises(PermissionError):w.command('integrity-gap-respond',self.payload())

    def test_hunch_and_next_action_are_retained_without_becoming_evidence_or_work(self):
        for kind, boundary in [('hunch','not evidence'),('next-action','not assigned or authorized')]:
            current=self.w.command('integrity-gap-read',self.card)
            p=dict(self.payload(),kind=kind,request_id=kind,expected=current['expected'])
            out=self.w.command('integrity-gap-respond',p)
            response=self.store.read(Ref(**out['ref']),self.w.scopes)['body']
            self.assertIsNone(response['evidence']);self.assertIn(boundary,response['authority'])
            self.assertEqual(response['status'],'awaiting-review')
            self.assertNotIn('integrity-gap-response',{r['kind'] for r in self.w.latest_records()
                if self.w.integrity_gaps.source_allowed(r,'domain:research')})
        self.assertEqual(self.store.read(self.ref,self.w.scopes),self.original)

    def test_unknown_gap_or_nonassessment_is_rejected(self):
        for p in [dict(self.payload(),key='invented'),dict(self.payload(),assessment=dict(id='SRC',revision=1))]:
            with self.assertRaises(ValueError):self.w.command('integrity-gap-respond',p)

    def test_diagnostic_gap_collects_clarification_without_becoming_an_assessment(self):
        body=deepcopy(self.original['body'])
        question='Does the documented fallback cover a category with no matching route?'
        body['clarification_requests']={'C1/P1/K1':dict(question=question,first_owner='Source owner')}
        body['gap_provenance']=dict(summary='Synthetic diagnostic excerpt; not a complete assessment.')
        ref=self.store.put('DIAGNOSTIC','integrity-gap-review','domain:research',body)
        card=next(c for c in self.w.integrity_gaps.state() if c['assessment']==asdict(ref))
        saved=deepcopy(self.store.read(ref,self.w.scopes))
        before=self.count()
        out=self.w.command('integrity-gap-read',card)
        self.assertEqual(self.count(),before)
        self.assertEqual(out['record_kind'],'integrity-gap-review')
        self.assertEqual(out['clarification_request']['question'],question)
        self.assertEqual(out['missing'],'Supply the transition rule.')
        self.assertEqual(out['responses'],[])
        self.assertEqual(len(self.w.latest_records('integrity-assessment')),1)
        # Normal approval and full-review routes must not accept this excerpt.
        for action in ('integrity-review-read','integrity-approve-domain'):
            with self.assertRaises(ValueError):
                self.w.command(action,dict(assessment=asdict(ref),disposition='approved',rationale='Test'))
        other=Workspace(self.store,'lee')
        with self.assertRaises(PermissionError):other.command('integrity-gap-read',card)
        p=dict(self.payload(),assessment=asdict(ref),key=card['key'])
        self.w.command('integrity-gap-respond',p)
        fresh=self.w.command('integrity-gap-read',card)
        self.assertEqual(fresh['status'],'uncertain')
        self.assertEqual(fresh['evidence_level'],'documentary-alignment')
        self.assertEqual(fresh['responses'][0]['status'],'awaiting-review')
        self.assertIn('not a governing decision',fresh['responses'][0]['authority'])
        self.assertEqual(self.store.read(ref,self.w.scopes),saved)
        self.assertEqual(self.store.read(self.ref,self.w.scopes),self.original)

    def test_shared_mapping_groups_only_identical_requests_and_keeps_occurrences(self):
        a=deepcopy(self.original);trace=a['body']['decision_trace']
        gap=deepcopy(trace['recommendation']['unresolved_material_gaps'][0]);gap.update(key='G2',obligation_ref='C2',part_ref='C2/P1/K1')
        trace['recommendation']['unresolved_material_gaps'].append(gap)
        part=deepcopy(trace['packet_findings'][0]['parts'][0]);part['part_ref']='C2/P1/K1';trace['packet_findings'][0]['parts'].append(part)
        self.assertEqual(len(self.w.integrity_gaps.cards(a)),2)
        trace['mapping_groups']=[dict(representative='C1',clause_refs=['C1','C2'],applicability=dict(status='shared'))]
        cards=self.w.integrity_gaps.cards(a);self.assertEqual(len(cards),1);self.assertEqual(len(cards[0]['occurrences']),2)
        gap['remaining_gap']='A different missing condition';self.assertEqual(len(self.w.integrity_gaps.cards(a)),2)


class GapHttpTests(unittest.TestCase):
    def setUp(self):
        from test_web import WebTests
        self.h=WebTests();self.h.setUp()
        store=Store(self.h.server.path);seed(store);store.close()
        self.h.post('profile',dict(actor='sam'))

    def tearDown(self):self.h.tearDown()

    def test_native_post_read_persist_and_session_guards(self):
        s=Store(self.h.server.path);c=Workspace(s,'sam').integrity_gaps.state()[0];s.close()
        p=dict(assessment=c['assessment'],key=c['key'],expected=None,request_id='http-one',kind='clarification',note='Synthetic HTTP test only.',actor='alex')
        self.assertEqual(self.h.post('integrity-gap-respond',p,{'X-CSRF-Token':''})[0],403)
        self.assertEqual(self.h.post('integrity-gap-respond',p,{'X-Workbench-Version':'999'})[0],409)
        status,out=self.h.post('integrity-gap-respond',p);self.assertEqual(status,200,out)
        status,c=self.h.post('integrity-gap-read',c);self.assertEqual(status,200,c)
        self.assertEqual(c['responses'][0]['actor'],'sam')
        self.h.post('profile',dict(actor='lee'));self.assertEqual(self.h.post('integrity-gap-read',c)[0],403)
