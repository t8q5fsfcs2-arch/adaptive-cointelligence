"""Submission events retain their own time, exact references and shared audience."""
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.project_timeline import timeline_page


class SubmissionTimelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'timeline.sqlite3')
        self.req=self.store.put('R','requirement',SCOPE,dict(title='A synthetic requirement',text='Preserve progress'))
    def tearDown(self):self.store.close();self.tmp.cleanup()
    def test_unlinked_review_has_one_submission_event_with_original_time_after_updates(self):
        body=dict(target=asdict(self.req),proposal=dict(text='Use a visible cue'),created_at='2026-11-01T15:00:00Z',created_by='alex')
        first=self.store.put('CASE','decision-case',SCOPE,body)
        self.store.put('CASE','decision-case',SCOPE,{**body,'updated_at':'2026-11-03T15:00:00Z'},first.revision)
        self.store.put('REV-1','human-review',SCOPE,dict(case=asdict(first),actor=dict(id='sam'),at='2026-11-02T15:00:00Z',rationale='Bounded evidence'))
        self.store.put('REV-2','human-review',SCOPE,dict(case=asdict(first),actor=dict(id='sam'),at='2026-11-04T15:00:00Z',rationale='Revised assessment'))
        before=[tuple(r) for r in self.store.db.execute('SELECT * FROM records')]
        events=timeline_page(self.store)['entries']
        opened=[e for e in events if e['category']=='Requirement review opened']
        self.assertEqual(len(opened),1);self.assertEqual(opened[0]['at'],body['created_at']);self.assertEqual(opened[0]['case'],asdict(first))
        submitted=[e for e in events if e['category']=='Requirement review submitted']
        self.assertEqual([e['at'] for e in submitted],['2026-11-04T15:00:00Z','2026-11-02T15:00:00Z'])
        self.assertTrue(all(e['actor']=='sam' and e['linked']==asdict(self.req) for e in submitted))
        self.assertEqual(before,[tuple(r) for r in self.store.db.execute('SELECT * FROM records')])
    def test_direction_assessment_links_exact_shared_case_and_excludes_private_or_undated_records(self):
        review=self.store.put('ASS','intake-assessment',SCOPE,dict(actor='lee',rationale='Useful with limits',at='2026-11-02T15:00:00Z'))
        first=self.store.put('INT-CASE','intake-case',SCOPE,dict(reviews=dict(lee=asdict(review))))
        self.store.put('INT-CASE','intake-case',SCOPE,dict(reviews=dict(lee=asdict(review)),status='published'),first.revision)
        for id,scope,at in [('SECRET','domain:research','2026-11-04T15:00:00Z'),('UNDATED',SCOPE,None),('INVALID',SCOPE,'not-a-date')]:
            self.store.put(id,'human-review',scope,dict(at=at,rationale='Not a timeline event'))
        events=timeline_page(self.store)['entries'];self.assertEqual(len(events),1)
        self.assertEqual(events[0]['intake_case'],asdict(first));self.assertEqual(events[0]['ref'],asdict(review));self.assertEqual(events[0]['category'],'Business direction review submitted')
