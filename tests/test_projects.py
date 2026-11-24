import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from unittest.mock import patch

from workbench.core import Store, StaleBasis
from workbench.intake import Intake, PRIVATE
from workbench.projects import Projects
import test_web


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.anchor = Path(self.tmp.name) / 'workbench.sqlite3'
        store = Store(self.anchor)
        intake = Intake(store, 'priya')
        intake.start({'title': 'Original initiative'})
        draft = intake.draft()
        intake.save({'step': 'value', 'expected': {'id': 'INTAKE-001', 'revision': draft['ref'].revision},
                     'business_challenge': 'Fictional users lose their progress.'})
        source = store.put('SOURCE-EXAMPLE', 'source', PRIVATE, {'text': 'Fictional source retained'})
        note = store.put('NOTE-EXAMPLE', 'note', PRIVATE, {'text': 'Fictional reasoning'})
        store.depend(note, source, {PRIVATE})
        store.packet('PACKET-EXAMPLE', 1, 'test recovery', [source, note], {PRIVATE}, {PRIVATE})
        store.close()
        self.original = self.dump(self.anchor)
        self.projects = Projects(self.anchor)

    def tearDown(self):
        self.tmp.cleanup()

    def dump(self, path):
        with sqlite3.connect(path) as db:
            return {table: db.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall()
                    for table in ('records', 'dependencies', 'packets')}

    def reset(self):
        with self.projects.locked('original', 1) as project:
            return self.projects.replace(project, {'confirm_title': 'Original initiative'}, 'priya')

    def test_register_existing_and_create_isolated_intake(self):
        self.assertEqual(self.dump(self.anchor), self.original)
        new = self.projects.create({'title': 'A second initiative'}, 'priya')['project_id']
        with self.projects.locked(new) as project:
            store = Store(project['path'])
            self.assertEqual(Intake(store, 'priya').draft()['body']['values']['business_challenge'], '')
            store.close()
        self.assertEqual(self.dump(self.anchor), self.original)
        self.assertEqual(len(self.projects.listing()), 2)

    def test_reset_retains_all_tables_and_restore_copies_snapshot(self):
        self.reset()
        history = self.projects.history('original')
        self.assertEqual(len(history), 1)
        with self.projects.locked('original', 2) as project:
            self.assertNotEqual(project['path'], str(self.anchor))
            self.assertEqual(self.dump(project['path'])['dependencies'], [])
            self.projects.replace(project, {'confirm_title': 'Original initiative', 'saved_version': history[0]['id']}, 'priya', True)
        with self.projects.locked('original', 3) as restored:
            self.assertNotEqual(restored['path'], str(self.anchor))
            self.assertEqual(self.dump(restored['path']), self.original)
            store = Store(restored['path'])
            store.put('NEW-NOTE', 'note', PRIVATE, {'text': 'Edited after restore'})
            store.close()
        self.assertEqual(self.dump(self.anchor), self.original)
        self.assertEqual(len(self.projects.history('original')), 2)

    def test_reset_and_restore_reject_stale_generation(self):
        self.reset()
        with self.assertRaises(StaleBasis):
            with self.projects.locked('original', 1):
                self.fail('Old tab must not reach the new intake even though record versions restart')

    def test_failed_preparation_keeps_current_pointer_and_work(self):
        with patch.object(self.projects, 'empty_intake', side_effect=OSError('Disk full')):
            with self.assertRaises(OSError):
                self.reset()
        with self.projects.locked('original', 1) as project:
            self.assertEqual(self.dump(project['path']), self.original)
        self.assertEqual(self.projects.history('original'), [])

    def test_permissions_confirmation_and_foreign_snapshot(self):
        new = self.projects.create({'title': 'Other'}, 'priya')['project_id']
        with self.assertRaises(PermissionError):
            self.projects.create({'title': 'No'}, 'sam')
        with self.projects.locked('original') as project:
            with self.assertRaises(ValueError):
                self.projects.replace(project, {'confirm_title': 'wrong'}, 'priya')
            with self.assertRaises(PermissionError):
                self.projects.replace(project, {'confirm_title': 'Original initiative'}, 'alex')
        self.reset()
        with self.projects.locked(new) as other:
            with self.assertRaises(ValueError):
                self.projects.replace(other, {'confirm_title': 'Other', 'saved_version': self.projects.history('original')[0]['id']}, 'priya', True)
        self.assertEqual(self.dump(self.anchor), self.original)

    def test_restart_retains_catalog_and_saved_versions(self):
        new = self.projects.create({'title': 'Second project'}, 'priya')['project_id']
        self.reset()
        reopened = Projects(self.anchor)
        self.assertEqual(len(reopened.listing()), 2)
        self.assertEqual(len(reopened.history('original')), 1)
        with reopened.locked('original', 2):
            pass
        with reopened.locked(new, 1):
            pass

    def test_reset_waits_for_inflight_write_then_retains_it(self):
        entered, release = threading.Event(), threading.Event()
        def author():
            with self.projects.locked('original', 1) as project:
                entered.set()
                release.wait(3)
                store = Store(project['path'])
                store.put('LATE-NOTE', 'note', PRIVATE, {'text': 'Completed before reset'})
                store.close()
        worker = threading.Thread(target=author)
        worker.start()
        self.assertTrue(entered.wait(3))
        resetter = threading.Thread(target=self.reset)
        resetter.start()
        self.assertTrue(resetter.is_alive())
        release.set()
        worker.join(3)
        resetter.join(3)
        self.assertFalse(resetter.is_alive())
        self.assertIn('LATE-NOTE', [row[0] for row in self.dump(self.anchor)['records']])
        self.assertEqual(len(self.projects.history('original')), 1)


class ProjectWebTests(unittest.TestCase):
    setUp = test_web.WebTests.setUp
    tearDown = test_web.WebTests.tearDown
    post = test_web.WebTests.post

    def state_for(self, project='original'):
        self.conn.request('GET', '/api/state?project='+project, headers={'Cookie': self.cookie})
        response = self.conn.getresponse()
        body = json.loads(response.read())
        self.assertEqual(response.status, 200, body)
        return body

    def test_switch_save_restart_and_stale_reset_tab(self):
        status, result = self.post('intake-start', {'title': 'Original'})
        self.assertEqual(status, 200, result)
        self.state = self.state_for()
        old = self.state['intake']['draft']['ref']
        self.assertEqual(self.post('intake-save', {'step': 'value', 'expected': old, 'business_challenge': 'Keep A'})[0], 200)
        status, result = self.post('project-create', {'title': 'New project'})
        self.assertEqual(status, 200, result)
        new = result['project_id']
        self.state = self.state_for(new)
        self.assertEqual(self.state['intake']['draft']['body']['values']['business_challenge'], '')
        self.assertEqual(self.post('intake-save', {'step': 'value', 'expected': self.state['intake']['draft']['ref'], 'business_challenge': 'Keep B'})[0], 200)
        self.state = self.state_for()
        self.assertEqual(self.state['intake']['draft']['body']['values']['business_challenge'], 'Keep A')
        self.assertEqual(self.post('project-reset', {'confirm_title': 'Original'})[0], 200)
        self.assertEqual(self.post('intake-save', {'step': 'value', 'expected': old, 'business_challenge': 'Stale tab'})[0], 409)
        self.state = self.state_for()
        self.assertEqual(self.state['intake']['draft']['body']['values']['business_challenge'], '')
        self.assertEqual(self.post('project-restore', {'confirm_title': 'Original', 'saved_version': self.state['saved_versions'][0]['id']})[0], 200)
        self.assertEqual(self.state_for()['intake']['draft']['body']['values']['business_challenge'], 'Keep A')
        self.assertEqual(self.state_for(new)['intake']['draft']['body']['values']['business_challenge'], 'Keep B')

    def test_api_requires_explicit_project_and_does_not_accept_path(self):
        self.assertEqual(self.post('intake-start', {'title': 'Test'}, {'X-Workbench-Project': ''})[0], 409)
        self.assertEqual(self.post('intake-start', {'title': 'Test'}, {'X-Workbench-Project': '../other.sqlite3'})[0], 403)
        self.assertEqual(self.post('intake-start', {'title': 'Test'}, {'X-Workbench-Version': '0'})[0], 409)
        self.assertFalse(self.state_for()['initialized'])
