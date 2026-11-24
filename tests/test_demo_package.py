from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.demo_package import initialize, workflow_check, MARKER
from workbench.model_provider import UnconfiguredModel
from workbench.workspace import Workspace

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('demo_bootstrap',ROOT/'run_demo.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)


class DemoPackageTests(TestCase):
    def test_complete_seed_is_offline_and_has_no_task_assignments_or_external_receipts(self):
        with TemporaryDirectory() as tmp,patch('socket.create_connection',side_effect=AssertionError('No network during seeding')):
            path=Path(tmp)/'demo.sqlite3';report=initialize(path)
            with closing(Store(path)) as store:
                design=Workspace(store,'lee',UnconfiguredModel())
                self.assertEqual(design.project_flow.requests(),[])
                self.assertEqual(design.demo_delivery.state()['receipts'],[])
                self.assertEqual(design.developer_briefs.state()['shared'][0]['body']['status'],'shared-for-review')
                self.assertEqual(design.domains.profile()['knowledge_entries'][0]['status'],'active')
                self.assertIn('rebuildable dependency graph',report['checks'])
                self.assertEqual(store.latest(MARKER,{SCOPE})['body']['package_version'],1)

    def test_relaunch_preserves_author_edits_and_changed_conversation_versions_exactly(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'demo.sqlite3';report=initialize(path)
            with closing(Store(path)) as store:
                w=Workspace(store,'sam',UnconfiguredModel())
                thread=w.domain_chat.owned(report['manifest']['research_conversation'])
                w.domain_chat.update(thread,review_mode='text')
                w.domain_chat.turn(thread,'user','A colleague’s saved exploration must survive a restart.')
                store.db.commit()
            before=path.read_bytes();initialize(path)
            self.assertEqual(path.read_bytes(),before)

    def test_existing_unowned_databases_are_rejected_without_schema_or_content_changes(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'real.sqlite3'
            with closing(sqlite3.connect(path)) as conn, conn:
                conn.execute('CREATE TABLE precious (value TEXT)')
                conn.execute("INSERT INTO precious VALUES ('keep')")
            before=path.read_bytes()
            with self.assertRaisesRegex(ValueError,'not a packaged demo'):initialize(path)
            self.assertEqual(path.read_bytes(),before)

    def test_failed_initialization_never_publishes_a_partial_database(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/'demo.sqlite3'
            with patch('workbench.demo_package.populate',side_effect=ValueError('interrupted fixture')):
                with self.assertRaisesRegex(ValueError,'interrupted fixture'):initialize(path)
            self.assertFalse(path.exists());self.assertEqual(list(Path(tmp).iterdir()),[])
            self.assertTrue(initialize(path)['checks'])

    def test_launcher_refuses_existing_unmanaged_directories_and_enforces_one_instance(self):
        with TemporaryDirectory() as tmp:
            existing=Path(tmp)/'real data';existing.mkdir();sentinel=existing/'keep.txt';sentinel.write_text('keep')
            with self.assertRaisesRegex(ValueError,'contains existing data'):bootstrap.state_directory(existing)
            self.assertEqual(sentinel.read_text(),'keep');self.assertEqual(list(existing.iterdir()),[sentinel])
            managed=bootstrap.state_directory(Path(tmp)/'demo with spaces')
            with bootstrap.demo_lock(managed):
                with self.assertRaisesRegex(ValueError,'already running'):
                    with bootstrap.demo_lock(managed):pass
            with bootstrap.demo_lock(managed):pass

    def test_http_workflow_and_model_configuration_isolation(self):
        with patch('workbench.web.load_model',side_effect=AssertionError('Never load personal credentials')):
            checks=workflow_check()
        self.assertIn('HTTP text upload, brief editing, preflight and repeat publication',checks)
        self.assertIn('Jira and ADO simulation receipts',checks)
        self.assertIn('database reopen and decision receipt',checks)
