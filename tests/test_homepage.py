"""Homepage metadata is read-only, role bounded and membership filtered."""
from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import asdict
import unittest
from workbench.core import Store
from workbench.intake import Intake, PRIVATE
from workbench.decisions import SCOPE
from workbench.projects import Projects
from workbench.clinic_demo import populate
import test_web

class HomepageMetadataTests(unittest.TestCase):
 def test_summary_reflects_real_drafts_and_published_work_without_source_text_or_writes(self):
  with TemporaryDirectory() as tmp:
   path=Path(tmp)/'home.sqlite3';store=Store(path);Intake(store,'priya').start({'title':'First initiative'});store.close();catalog=Projects(path)
   rows=catalog.listing(actor='priya');self.assertEqual(rows[0]['summary']['brief_status'],'draft');self.assertEqual(rows[0]['summary']['stage'],'Context')
   store=Store(path);i=Intake(store,'priya');i.save({'expected':asdict(i.draft()['ref']),'step':'value','business_challenge':'Private sponsor wording'})
   store.put('PRIVATE-SOURCE','intake-source',PRIVATE,{'text':'Confidential source content'});store.put('DESIGN-SECRET','contribution-draft','domain:design',{'saved_at':'2099-01-01','text':'Private Design wording'})
   before=list(store.db.iterdump());row=catalog.listing(actor='priya')[0];self.assertEqual(row['summary']['stage'],'Business Intent');self.assertEqual(row['summary']['source_count'],1);self.assertNotIn('2099',row['summary']['last_activity']);self.assertNotIn('Private',str(row));self.assertNotIn('Confidential',str(row));self.assertEqual(before,list(store.db.iterdump()));store.close()
   self.assertNotIn('summary',catalog.listing(actor='sam')[0]);self.assertEqual(catalog.listing(actor='priya',allowed_ids=set()),[])
 def test_published_project_row_retains_exact_intent_revision_and_publication_date(self):
  with TemporaryDirectory() as tmp:
   path=Path(tmp)/'published.sqlite3';s=Store(path);populate(s);catalog=Projects(path);row=catalog.listing(actor='priya')[0];intent=s.latest('INT-001',{SCOPE});self.assertEqual(row['summary']['brief_status'],'published');self.assertEqual(row['summary']['brief_revision'],intent['ref'].revision);self.assertEqual(row['summary']['stage'],'Project dashboard');self.assertIsNotNone(row['summary']['published_at']);s.close()

class HomepageAssetTests(unittest.TestCase):
 def test_homepage_assets_are_served_with_matching_original_icons(self):
  h=test_web.WebTests();h.setUp()
  try:
   for path,expected in [('/home.js',b'sponsorHome'),('/home.css',b'home-hero'),('/home-target.svg',b'<svg'),('/home-book-open.svg',b'<svg')]:
    h.conn.request('GET',path);r=h.conn.getresponse();self.assertEqual(r.status,200);self.assertIn(expected,r.read())
  finally:h.tearDown()
