#!/usr/bin/env python3
"""Create an isolated demo environment and start the Workbench. Python 3.12+."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import sys
import venv

ROOT = Path(__file__).resolve().parent
OWNER = {"application": "adaptive-cointelligence-demo", "format": 1}


def state_directory(path):
    if path.is_symlink():
        raise ValueError('Choose a real demo directory, not a symbolic link.')
    path = path.resolve()
    marker = path / '.demo-owner.json'
    if marker.exists():
        if json.loads(marker.read_text()) != OWNER:
            raise ValueError('This directory belongs to a different application. Nothing was changed.')
    else:
        if path.exists() and any(path.iterdir()):
            raise ValueError('The chosen directory contains existing data. Choose a new empty directory; nothing was changed.')
        path.mkdir(parents=True, exist_ok=True)
        try:
            with marker.open('x') as out:
                json.dump(OWNER, out)
        except FileExistsError:
            if json.loads(marker.read_text()) != OWNER:
                raise ValueError('A different application initialized this directory.') from None
    return path


@contextmanager
def demo_lock(path):
    """One launcher owns this environment; a crash releases the OS lock."""
    with (path / '.launcher.lock').open('a+b') as lock:
        if not os.fstat(lock.fileno()).st_size:
            lock.write(b'0')
            lock.flush()
        lock.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise ValueError('This demo is already running or being installed. Use its existing browser link.') from None
        try:
            yield
        finally:
            if os.name == 'nt':
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock, fcntl.LOCK_UN)


def environment(path, *, offline=False):
    home = path / 'venv'
    python = home / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating the isolated demo Python environment…', flush=True)
        venv.EnvBuilder(with_pip=True).create(home)
    lock = ROOT / 'requirements-demo.txt'
    stamp = home / '.requirements-sha256'
    digest = hashlib.sha256(lock.read_bytes()).hexdigest()
    required = [line.split(' --hash=')[0].split('==') for line in lock.read_text().splitlines() if line and not line.startswith('#')]
    check = 'import importlib.metadata as m; expected='+repr(required)+'; assert all(m.version(k)==v for k,v in expected)'
    probe = subprocess.run([str(python), '-c', check], capture_output=True)
    if probe.returncode or not stamp.exists() or stamp.read_text() != digest:
        wheelhouse = ROOT / 'wheelhouse'
        if offline and not wheelhouse.is_dir():
            raise ValueError('Offline installation needs the wheelhouse included in the developer package.')
        local = ['--no-index', '--find-links', str(wheelhouse)] if offline else []
        print('Installing the pinned demo dependencies '+('(offline)…' if offline else '(internet needed on first run)…'), flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check',
                        '--require-hashes', '--only-binary=:all:', '--no-deps', *local, '-r', str(lock)], check=True)
        stamp.write_text(digest)
    return python


def source_snapshot(root=ROOT):
    """Modification times of the files the running server loads at start: Python modules and JSON configuration."""
    found = {}
    for base in (root / 'src', root / 'config'):
        if not base.exists():
            continue
        for path in base.rglob('*'):
            if path.suffix in {'.py', '.json'} and '__pycache__' not in path.parts and path.is_file():
                try:
                    found[str(path)] = path.stat().st_mtime_ns
                except OSError:
                    pass
    return found


def stop(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run_with_reload(command, env, *, interval=1.0, snapshot=source_snapshot, sleep=time.sleep, popen=subprocess.Popen, out=lambda message: print(message, flush=True)):
    """Restart the demo server when its Python or configuration files change. Saved demo data is kept.
    Screens and styles are read fresh on every request, so those changes only need a browser refresh."""
    baseline = snapshot()
    process = popen(command, cwd=ROOT, env=env)
    try:
        while True:
            sleep(interval)
            if process.poll() is not None:
                return process.returncode
            current = snapshot()
            if current != baseline:
                baseline = current
                out('Code changed; restarting the demo. Your saved data is kept. Refresh the browser in a moment.')
                stop(process)
                process = popen(command, cwd=ROOT, env=env)
    except KeyboardInterrupt:
        stop(process)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8770, help='Loopback port (default: 8770)')
    parser.add_argument('--state-dir', type=Path, default=ROOT / '.demo', help='New or package-owned demo directory')
    parser.add_argument('--check', action='store_true', help='Run the full workflow and HTTP checks in a temporary database, then exit')
    parser.add_argument('--offline', action='store_true', help='Install only from the developer package wheelhouse; never contact a package index')
    parser.add_argument('--reload', action='store_true', help='Restart the server automatically when code changes; saved demo data is kept')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 12):
        parser.exit(1, 'Python 3.12 or newer is required. Install it, then run this command again.\n')
    if not 1 <= args.port <= 65535:
        parser.error('Choose a port from 1 to 65535.')
    try:
        folder = state_directory(args.state_dir)
        with demo_lock(folder):
            python = environment(folder, offline=args.offline)
            env = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), PYTHONDONTWRITEBYTECODE='1')
            command = [str(python), '-m', 'workbench.demo_package', '--data-dir', str(folder / 'data'), '--port', str(args.port)]
            if args.check:
                command.append('--check')
            elif args.reload:
                print('Auto-reload is on: code changes restart the server and keep your data.', flush=True)
                return run_with_reload(command, env)
            process = subprocess.Popen(command, cwd=ROOT, env=env)
            try:
                return process.wait()
            except KeyboardInterrupt:
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait(timeout=5)
                return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print('Could not start the demo: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
