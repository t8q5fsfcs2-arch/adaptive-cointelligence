"""Readable project references stay distinct from titles, versions and store identity."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.projects import Projects
from workbench.project_connections import connect, fingerprint, readonly
from workbench.workspace import Workspace

class ProjectReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.path=Path(self.tmp.name)/'workbench.sqlite3'
        with closing(Store(self.path)) as store:Workspace(store,'priya').command('intake-start',{'title':'Same product'})
        self.projects=Projects(self.path)
    def tearDown(self):self.tmp.cleanup()
    def info(self,id='original'):return self.projects.info(self.projects.current(id))
    def test_same_names_have_distinct_codes_and_reopening_reads_do_not_reallocate(self):
        other=self.projects.create({'title':'Same product'},'priya')['project_id']
        first,second=self.info(),self.info(other)
        self.assertEqual(first['reference'],'WB-001');self.assertEqual(second['reference'],'WB-002')
        self.assertEqual(first['title'],second['title']);self.assertNotEqual(first['display_title'],second['display_title'])
        self.assertEqual(first['display_title'],'WB-001 · v1 — Same product')
        for _ in range(3):self.projects=Projects(self.path);self.info();self.projects.listing()
        next=self.projects.create({'title':'Third product'},'priya')['project_id']
        self.assertEqual(self.info(next)['reference'],'WB-003')
    def test_rename_reset_restore_keep_code_and_raw_name_confirmation(self):
        with closing(Store(self.path)) as store:
            project=store.latest('PROJECT-001',{SCOPE});body=deepcopy(project['body']);body['title']='Renamed product'
            store.put('PROJECT-001','project',SCOPE,body,project['ref'].revision)
        self.assertEqual(self.info()['reference'],'WB-001');self.assertEqual(self.info()['title'],'Renamed product')
        with self.assertRaises(ValueError):self.projects.replace(self.projects.current('original'),{'confirm_title':self.info()['display_title']},'priya')
        self.projects.replace(self.projects.current('original'),{'confirm_title':'Renamed product'},'priya')
        self.assertEqual(self.info()['display_title'],'WB-001 · v2 — Renamed product')
        saved=self.projects.history('original')[0]
        self.projects.replace(self.projects.current('original'),{'confirm_title':'Renamed product','saved_version':saved['id']},'priya',restore=True)
        self.assertEqual(self.info()['reference'],'WB-001');self.assertEqual(self.info()['version'],3)
    def test_legacy_catalog_backfill_and_connections_do_not_modify_source_records(self):
        with readonly(self.path) as db:before=fingerprint(db)
        with self.projects.db() as db:db.execute('DROP TABLE project_references')
        self.projects=Projects(self.path)
        self.assertEqual(self.info()['reference'],'WB-001')
        source=Path(self.tmp.name)/'other.sqlite3'
        with closing(Store(source)) as store:Workspace(store,'priya').command('intake-start',{'title':'Same product'})
        old=Projects(source)
        for label in ('Version A','Version B'):
            # Different source catalogs retain independent project identity.
            if label.startswith('Version B'):
                source=Path(self.tmp.name)/'third.sqlite3'
                with closing(Store(source)) as store:Workspace(store,'priya').command('intake-start',{'title':'Same product'})
                old=Projects(source)
            linked=connect(self.projects,old.catalog,label)[0]['project_id'];meta=self.info(linked)
            self.assertEqual(meta['origin'],label);self.assertNotIn(label,meta['display_title'])
        refs=[p['reference'] for p in self.projects.listing()];self.assertEqual(len(refs),len(set(refs)))
        with readonly(self.path) as db:self.assertEqual(fingerprint(db),before)
    def test_concurrent_project_creation_allocates_unique_references(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            ids=list(pool.map(lambda _:self.projects.create({'title':'Same product'},'priya')['project_id'],range(2)))
        self.assertEqual({self.info(id)['reference'] for id in ids},{'WB-002','WB-003'})
