from contextlib import closing, redirect_stdout
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from workbench.core import Store
from workbench.decisions import SCOPE
from workbench.model_provider import ModelUnavailable, UnconfiguredModel

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reviewer_launcher', ROOT / 'reviewer_launcher.py')
reviewer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reviewer)


class HTTPReview:
    def __init__(self, controller):
        self.connection = http.client.HTTPConnection('127.0.0.1', controller.server.server_port, timeout=10)
        self.cookie = ''
        self.state = {}

    def request(self, method, path, data=None):
        headers = {'Cookie': self.cookie}
        if data is not None:
            headers.update({'Content-Type': 'application/json', 'X-CSRF-Token': self.state['csrf'],
                            'X-Workbench-Project': 'original', 'X-Workbench-Version': '1'})
        self.connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
        response = self.connection.getresponse()
        raw = response.read()
        if response.getheader('Set-Cookie'):
            self.cookie = response.getheader('Set-Cookie').split(';')[0]
        result = json.loads(raw) if 'application/json' in response.getheader('Content-Type', '') else raw
        if path == '/api/state' and response.status == 200:
            self.state = result
        return response.status, result

    def close(self):
        self.connection.close()


class ReviewerLauncherTests(TestCase):
    def test_default_storage_lives_outside_the_application_for_each_platform(self):
        home = Path('/reviewer-home')
        self.assertEqual(reviewer.default_state_directory(platform='darwin', home=home), home / 'Library/Application Support/Adaptive Cointelligence Reviewer')
        self.assertEqual(reviewer.default_state_directory(platform='win32', home=home, environment={'LOCALAPPDATA': '/local-data'}), Path('/local-data/Adaptive Cointelligence Reviewer'))
        for platform in ('linux', 'win32'):
            self.assertEqual(reviewer.default_state_directory(platform=platform, home=home, environment={}), home / '.local/share/Adaptive Cointelligence Reviewer')

    def test_actual_server_stays_loopback_and_unconfigured_despite_inherited_credentials_and_admin_attempts(self):
        with TemporaryDirectory() as tmp, patch.dict(os.environ, {'OPENAI_API_KEY': 'unused-synthetic-value', 'ANTHROPIC_API_KEY': 'unused-synthetic-value', 'COACH_CONFIG_FILE': '/never-load-personal-config'}), \
                patch('workbench.web.load_model', side_effect=AssertionError('Never load environment model credentials')), \
                patch('workbench.model_connection.ModelConnections', side_effect=AssertionError('Reviewer must not enable managed model settings')), \
                patch('workbench.model_provider.urlopen', side_effect=AssertionError('No provider calls')):
            controller = reviewer.ReviewerController(Path(tmp) / 'review with spaces').start()
            client = HTTPReview(controller)
            try:
                self.assertTrue(controller.running)
                self.assertEqual(controller.server.server_address[0], '127.0.0.1')
                self.assertGreater(controller.server.server_port, 0)
                self.assertIsInstance(controller.server.model, UnconfiguredModel)
                self.assertIsNone(controller.server.model_connection)
                self.assertIn('AI model calls disabled', controller.server.workspace_notice)
                with self.assertRaises(ModelUnavailable):
                    controller.server.model.generate(instructions='', context={}, schema={})
                status, state = client.request('GET', '/api/state')
                self.assertEqual(status, 200)
                self.assertIsNone(state['model_connection'])
                for asset in ('/', '/app.js', '/workspace.css', '/domain-chat.js', '/inter-latin.woff2'):
                    self.assertEqual(client.request('GET', asset)[0], 200, asset)
                self.assertEqual(client.request('POST', '/api/profile', {'actor': 'administrator'})[0], 200)
                self.assertEqual(client.request('GET', '/api/state')[0], 200)
                self.assertEqual(client.request('GET', '/api/model-connections')[0], 403)
                for action in ('save', 'test', 'assign', 'remove'):
                    self.assertEqual(client.request('POST', '/api/model-connection-'+action, {})[0], 403, action)
                self.assertFalse((controller.state_dir / 'model-connections.json').exists())
            finally:
                client.close()
                controller.stop()
            self.assertFalse(controller.running)
            self.assertIsNone(controller.url)

    def test_stop_closes_the_listener_and_restart_preserves_saved_work_without_reseeding(self):
        with TemporaryDirectory() as tmp:
            controller = reviewer.ReviewerController(Path(tmp) / 'saved review').start()
            port = controller.server.server_port
            try:
                with closing(Store(controller.database)) as store, store.transaction():
                    saved = store.put('REVIEWER-SAVED-NOTE', 'evidence', SCOPE, {'text': 'A reviewer-authored observation must survive restart.'}, 0)
            finally:
                controller.stop()
            controller.stop()
            with socket.socket() as probe:
                probe.settimeout(1)
                self.assertNotEqual(probe.connect_ex(('127.0.0.1', port)), 0)
            restarted = reviewer.ReviewerController(controller.state_dir).start()
            try:
                with closing(Store(restarted.database)) as store:
                    self.assertEqual(store.read(saved, {SCOPE})['body']['text'], 'A reviewer-authored observation must survive restart.')
                    self.assertEqual(store.latest(saved.id, {SCOPE})['ref'].revision, 1)
            finally:
                restarted.stop()

    def test_one_controller_is_idempotent_and_a_second_cannot_own_the_same_directory(self):
        with TemporaryDirectory() as tmp:
            first = reviewer.ReviewerController(Path(tmp) / 'one reviewer').start()
            second = reviewer.ReviewerController(first.state_dir)
            try:
                server = first.server
                self.assertIs(first.start(), first)
                self.assertIs(first.server, server)
                with self.assertRaisesRegex(ValueError, 'already running'):
                    second.start()
                self.assertFalse(second.running)
            finally:
                first.stop()
            try:
                second.start()
                self.assertTrue(second.running)
            finally:
                second.stop()

    def test_unmanaged_directories_and_databases_are_refused_without_altering_their_contents(self):
        with TemporaryDirectory() as tmp:
            folder = Path(tmp) / 'unmanaged'
            folder.mkdir()
            sentinel = folder / 'keep.txt'
            sentinel.write_text('keep this unrelated data')
            with self.assertRaisesRegex(ValueError, 'contains existing data'):
                reviewer.ReviewerController(folder).start()
            self.assertEqual(list(folder.iterdir()), [sentinel])
            self.assertEqual(sentinel.read_text(), 'keep this unrelated data')
            managed = reviewer.state_directory(Path(tmp) / 'managed')
            database = managed / 'data/workbench.sqlite3'
            database.parent.mkdir()
            with closing(sqlite3.connect(database)) as db, db:
                db.execute('CREATE TABLE precious (value TEXT)')
                db.execute("INSERT INTO precious VALUES ('keep')")
            before = database.read_bytes()
            with self.assertRaisesRegex(ValueError, 'not a packaged demo'):
                reviewer.ReviewerController(managed).start()
            self.assertEqual(database.read_bytes(), before)

    def test_an_occupied_port_releases_ownership_so_the_saved_demo_can_be_retried(self):
        with TemporaryDirectory() as tmp, socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            occupied.listen()
            controller = reviewer.ReviewerController(Path(tmp) / 'port conflict', occupied.getsockname()[1])
            with self.assertRaises(OSError):
                controller.start()
            self.assertFalse(controller.running)
            retry = reviewer.ReviewerController(controller.state_dir)
            try:
                retry.start()
                self.assertTrue(retry.running)
            finally:
                retry.stop()

    def test_check_uses_disposable_workflow_without_creating_a_reviewer_directory(self):
        with TemporaryDirectory() as tmp, patch.object(reviewer, 'workflow_check', return_value=['offline workflow']) as check:
            target = Path(tmp) / 'must not be created'
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(reviewer.main(['--check', '--state-dir', str(target), '--no-browser']), 0)
            check.assert_called_once_with()
            self.assertFalse(target.exists())
            self.assertEqual(json.loads(output.getvalue())['external_model_calls'], 0)

    def test_isolated_python_bootstrap_finds_the_package_without_pythonpath(self):
        result = subprocess.run([sys.executable, '-I', str(ROOT / 'reviewer_launcher.py'), '--check'],
                                cwd=ROOT.parent, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['external_model_calls'], 0)
        self.assertIn('HTTP UI/assets and all four personas', report['checks'])
