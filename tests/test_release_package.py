"""Release boundary checks: provenance, traversal, credentials and offline setup."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_release', ROOT/'scripts/build_release.py')
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
spec = importlib.util.spec_from_file_location('run_demo_release_test', ROOT/'run_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class ReleaseTests(unittest.TestCase):
    def test_unsafe_archive_members_refused(self):
        for name in ('../escape', '/absolute', 'python/../../escape', 'C:/file', 'python\\escape'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                release.safe_name(name)

    def test_wrong_hash_refused_before_reading_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp)/'not-a-wheel'
            file.write_text('wrong artifact')
            with self.assertRaisesRegex(ValueError, 'Checksum mismatch'):
                release.checked(file, '0'*64)

    def test_dirty_or_sensitive_tracked_inputs_are_refused(self):
        with patch.object(release.subprocess, 'check_output', return_value=b' M source'):
            with self.assertRaisesRegex(ValueError, 'clean checkout'):
                release.source_files()
        for filename in ('.env', 'runtime/key.pem', 'runtime/model-connections.json', 'saved.sqlite3'):
            with patch.object(release.subprocess, 'check_output', side_effect=[b'', filename.encode()+b'\0']):
                with self.subTest(filename=filename), self.assertRaisesRegex(ValueError, 'Disallowed'):
                    release.source_files()

    def test_source_allowlist_excludes_untracked_and_old_model_results(self):
        required=['reviewer_launcher.py','run_demo.py','src/workbench/static/index.html','docs/CONNECTOR_CAPABILITIES.md']
        tracked=required+['src/workbench/model_provider.py','docs/adr/0038-admin-model-connections.md','docs/evaluation/old.json']
        with patch.object(release.subprocess, 'check_output', side_effect=[b'', ('\0'.join(tracked)+'\0').encode()]):
            selected=release.source_files()
        self.assertEqual(selected, tracked[:-1])
        self.assertNotIn('.demo/data/workbench.sqlite3',selected)

    def test_manifest_matches_files_and_preserves_executable_mode_in_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'AdaptiveCointelligence'
            folder.mkdir()
            launcher=folder/'launch'
            launcher.write_text('#!/bin/sh\nexit 0\n')
            launcher.chmod(0o755)
            release.manifest(folder,dict(source_commit='abc',fictional_data_only=True))
            body=json.loads((folder/'PACKAGE-MANIFEST.json').read_text())
            self.assertEqual(body['files'][0]['sha256'],release.digest(launcher))
            release.archive(folder,Path(tmp)/'release.zip')
            with zipfile.ZipFile(Path(tmp)/'release.zip') as archive:
                self.assertTrue(archive.getinfo('AdaptiveCointelligence/launch').external_attr>>16 & 0o100)
                self.assertIsNone(archive.testzip())

    def test_offline_installer_has_no_index_and_hash_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'source'
            root.mkdir()
            (root/'requirements-demo.txt').write_text('networkx==3.7 --hash=sha256:x\n')
            (root/'wheelhouse').mkdir()
            state=Path(tmp)/'state'
            executable=state/('venv/Scripts/python.exe' if os.name=='nt' else 'venv/bin/python')
            executable.parent.mkdir(parents=True)
            executable.touch()
            with patch.object(demo,'ROOT',root), patch.object(demo.subprocess,'run') as run:
                run.return_value.returncode=1
                demo.environment(state,offline=True)
            command=run.call_args_list[-1].args[0]
            self.assertIn('--no-index',command)
            self.assertIn('--require-hashes',command)
            self.assertIn('--find-links',command)


if __name__=='__main__':
    unittest.main()
