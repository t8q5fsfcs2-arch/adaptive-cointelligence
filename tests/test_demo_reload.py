import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('run_demo_module', ROOT / 'run_demo.py')
run_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_demo)


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.terminated = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


class DemoReloadTests(unittest.TestCase):
    def test_snapshot_tracks_python_and_json_only(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'src' / 'pkg' / '__pycache__').mkdir(parents=True)
            (root / 'config').mkdir()
            (root / 'src' / 'pkg' / 'a.py').write_text('x=1')
            (root / 'src' / 'pkg' / 'app.js').write_text('1')
            (root / 'src' / 'pkg' / '__pycache__' / 'a.cpython.py').write_text('')
            (root / 'config' / 'domains.json').write_text('{}')
            names = {Path(p).name for p in run_demo.source_snapshot(root)}
            self.assertEqual(names, {'a.py', 'domains.json'})

    def test_restarts_on_change_keeps_running_and_stops_on_interrupt(self):
        snapshots = iter([{'a': 1}, {'a': 1}, {'a': 2}, {'a': 2}])
        started, messages = [], []

        def popen(command, cwd, env):
            started.append(FakeProcess())
            return started[-1]

        ticks = iter([None, None, KeyboardInterrupt()])

        def sleep(_):
            tick = next(ticks)
            if isinstance(tick, BaseException):
                raise tick

        code = run_demo.run_with_reload(['server'], {}, snapshot=lambda: next(snapshots), sleep=sleep, popen=popen, out=messages.append)
        self.assertEqual(code, 0)
        self.assertEqual(len(started), 2)
        self.assertTrue(started[0].terminated)
        self.assertTrue(started[1].terminated)
        self.assertIn('saved data is kept', messages[0])

    def test_returns_when_the_server_exits_on_its_own(self):
        process = FakeProcess()
        process.returncode = 3
        code = run_demo.run_with_reload(['server'], {}, snapshot=lambda: {}, sleep=lambda _: None, popen=lambda *a, **k: process, out=lambda m: None)
        self.assertEqual(code, 3)


if __name__ == '__main__':
    unittest.main()
