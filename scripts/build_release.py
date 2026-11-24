#!/usr/bin/env python3
"""Build private offline reviewer packages from a clean, committed checkout.

Inputs are a pinned runtime cache and hash-locked wheels; no download or model call
is performed. Source selection is explicit and never walks local runtime folders.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIMES = {
    'mac-arm64': ('aarch64-apple-darwin', '3ee3ee547cedfeb7c2b16b2b7156039f7b470bb8f857e226fd3d2eb11db83c76'),
    'mac-x64': ('x86_64-apple-darwin', '2e31b23f3f1319f707d0e620b48847a0046577541d357276821f9f1b5492e0ba'),
    'windows-x64': ('x86_64-pc-windows-msvc', 'e90c1b6419da3bd812dd73bb3de40287a21abf153438147639ec5e20375ea93f'),
}
VERSION = '3.12.14+20260901'
DEPS = {
    'networkx-3.7-py3-none-any.whl': 'e3fd2c13a7814cee3746340d8d7f8598a67f16a58bf47fb7f8793fab6efca1b0',
    'pypdf-6.21.4-py3-none-any.whl': '33e4fb41ca352810eb4e9838aa0d82d6888a5f8bf682f43e99cce5faa666255c',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(path, expected):
    if digest(path) != expected:
        raise ValueError('Checksum mismatch: ' + str(path))
    return path


def safe_name(name):
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('Unsafe archive member: ' + name)
    return path


def source_files():
    """Only committed source/configuration/docs; historical model-result JSON omitted."""
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise ValueError('Commit the reviewed source first; release builds require a clean checkout.')
    names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    selected = []
    for name in filter(None, names):
        safe_name(name)
        path = Path(name)
        if (path.name.startswith('.env') or path.suffix in {'.db', '.sqlite', '.sqlite3', '.log', '.pem', '.key'}
                or path.name == 'model-connections.json' or '__pycache__' in path.parts):
            raise ValueError('Disallowed tracked release input: ' + name)
        if name.startswith('docs/evaluation/') and name.endswith('.json'):
            continue
        if (ROOT / name).is_symlink():
            raise ValueError('Unexpected source symlink: ' + name)
        selected.append(name)
    for required in ('reviewer_launcher.py', 'run_demo.py', 'src/workbench/static/index.html', 'docs/CONNECTOR_CAPABILITIES.md'):
        if required not in selected:
            raise ValueError('Missing release source: ' + required)
    return selected


def copy_files(names, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)


def vendor(wheelhouse, destination):
    destination.mkdir(parents=True)
    for filename, expected in DEPS.items():
        with zipfile.ZipFile(checked(wheelhouse / filename, expected)) as wheel:
            for item in wheel.infolist():
                safe_name(item.filename)
                if stat.S_ISLNK(item.external_attr >> 16):
                    raise ValueError('Unexpected wheel symlink.')
            wheel.extractall(destination)


def runtime(cache, key, destination):
    target, expected = RUNTIMES[key]
    filename = 'cpython-' + VERSION + '-' + target + '-install_only.tar.gz'
    source = checked(cache / filename, expected)
    destination.mkdir(parents=True)
    with tarfile.open(source) as archive:
        for member in archive.getmembers():
            safe_name(member.name)
            if not member.name.startswith('python/') and member.name != 'python':
                raise ValueError('Runtime must be rooted in python/.')
        archive.extractall(destination, filter='data')
    return dict(version=VERSION, filename=filename, sha256=expected,
                source='https://github.com/astral-sh/python-build-standalone/releases/download/20260901/' + filename.replace('+', '%2B'))


def manifest(folder, metadata):
    files = []
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            files.append(dict(path=path.relative_to(folder).as_posix(), symlink=os.readlink(path)))
        elif path.is_file():
            files.append(dict(path=path.relative_to(folder).as_posix(), bytes=path.stat().st_size, sha256=digest(path)))
    (folder / 'PACKAGE-MANIFEST.json').write_text(json.dumps(dict(**metadata, files=files), indent=2) + '\n')


def archive(folder, destination):
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for path in sorted(folder.rglob('*')):
            name = (Path(folder.name) / path.relative_to(folder)).as_posix()
            if path.is_symlink():
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = (stat.S_IFLNK | 0o777) << 16
                out.writestr(info, os.readlink(path))
            elif path.is_file():
                out.write(path, name)


GUIDE = '''ADAPTIVE COINTELLIGENCE

This is a local prototype review package with fictional clinic starting data.
No actual source files, author workspaces or credentials are included.
Saved example conversations are labelled scripted; they are not live AI results.

{launch}

Your default browser opens the Workbench. Keep the small console window open.
Its Workbench link reopens the browser. Press Ctrl+C in the console when finished.
Run the launcher again to resume your saved work. The same data is reused without
resetting it. A second launch is refused while the first is running.

Saved work: {state}
Keep this folder if you remove or replace the downloaded application package.
For a fresh example, use an explicitly new --state-dir; never overwrite old work.

Start with Home and select the fictional clinic project. Switch local roles in
the menu to follow Business development, Research, Design, Shared requirements,
Shared Accountability and delivery staging. Roles are a local review convenience,
not enterprise authentication. Browser data and draft text are local to this origin;
saved application records persist in the workspace folder.

Integrity Review has no live model in this launcher. Paid model calls are disabled,
including connection-test actions. Connector implementations are included in the
source, but no vendor is connected. Jira/ADO actions are labelled local simulations.
See app/docs/CONNECTOR_CAPABILITIES.md.
The developer package has the opt-in configuration path for separately authorized
model or vendor use. Do not put confidential material into a shared review demo.

Python and the two application dependencies are included; no Python install or
internet connection is needed to start. PDF text extraction is included; optional
PDF image review needs separate Poppler tools and an authorized vision connection.

These command launchers have no signed installer or Mac notarization.
Your organization's device policy may require IT approval. Windows x64 is supplied;
Windows ARM is not a native target in this release. Review PACKAGE-MANIFEST.json
and the companion download SHA256SUMS.txt before redistribution. Source licensing
is not granted merely
by providing this prototype; third-party licenses remain included with components.

This package demonstrates workflow and inspectable history. It does not establish
semantic accuracy, enterprise readiness or business value from real team use.
'''


def build(cache, wheelhouse, output):
    names = source_files()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    output.mkdir(parents=True, exist_ok=False)
    meta = dict(application='Adaptive Cointelligence', source_commit=commit,
                fictional_data_only=True, paid_calls_in_reviewer_launcher=False,
                source_exclusions=['historical docs/evaluation/*.json', 'all untracked/ignored files and .git'],
                dependency_wheels=DEPS)
    developer = output / 'AdaptiveCointelligence-Developer'
    copy_files(names, developer)
    (developer / 'wheelhouse').mkdir()
    for filename, expected in DEPS.items():
        shutil.copy2(checked(wheelhouse / filename, expected), developer / 'wheelhouse' / filename)
    (developer / 'START HERE.txt').write_text('ADAPTIVE COINTELLIGENCE DEVELOPER HANDOFF\n\nRead docs/PACKAGING.md, docs/CONNECTOR_CAPABILITIES.md and CLAUDE.md.\nPython 3.12+ required for source development.\n\nOffline first launch:\n  python run_demo.py --offline --check\n  python run_demo.py --offline\n\nThe business-reviewer launcher disables live models. The developer demo path\nallows separately configured, explicitly authorized model use. Never bundle keys.\n')
    manifest(developer, dict(**meta, audience='developer'))
    archive(developer, output / 'AdaptiveCointelligence-Developer.zip')

    # Keep the same auditable source/configuration/docs in every distribution.
    app_names = names
    mac = output / 'AdaptiveCointelligence-Review-macOS'
    copy_files(app_names, mac / 'app')
    vendor(wheelhouse, mac / 'app' / 'vendor')
    runtimes = {key:runtime(cache,key,mac / 'runtimes' / key) for key in ('mac-arm64','mac-x64')}
    executable = mac / 'Open Adaptive Cointelligence.command'
    executable.write_text('''#!/bin/sh
set -eu
resources="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
# Script launchers can start under Rosetta; select the actual hardware target.
if [ "$(/usr/sbin/sysctl -n hw.optional.arm64 2>/dev/null || true)" = "1" ]; then
  target=mac-arm64
else
  target=mac-x64
fi
exec "$resources/runtimes/$target/python/bin/python3" -I -B "$resources/app/reviewer_launcher.py" "$@"
''')
    executable.chmod(0o755)
    (mac / 'START HERE.txt').write_text(GUIDE.format(launch='MAC: Extract the ZIP fully. Double-click Open Adaptive Cointelligence.command. Terminal\nopens a small console and your default browser opens the Workbench. Both Apple\nSilicon and Intel Macs are supported (macOS 12 or newer).',state='~/Library/Application Support/Adaptive Cointelligence Reviewer'))
    manifest(mac, dict(**meta, audience='business reviewer', platforms=['macOS arm64','macOS x86_64'], runtimes=runtimes))
    archive(mac, output / 'AdaptiveCointelligence-Review-macOS.zip')

    windows = output / 'AdaptiveCointelligence-Review-Windows'
    copy_files(app_names, windows / 'app')
    vendor(wheelhouse, windows / 'app' / 'vendor')
    windows_runtime = runtime(cache,'windows-x64',windows / 'runtime')
    (windows / 'Open Adaptive Cointelligence.cmd').write_bytes(b'@echo off\r\nsetlocal\r\n"%~dp0runtime\\python\\python.exe" -I -B "%~dp0app\\reviewer_launcher.py" %*\r\nif errorlevel 1 pause\r\n')
    (windows / 'START HERE.txt').write_text(GUIDE.format(launch='WINDOWS: Extract the entire ZIP to a normal folder first. Double-click\nOpen Adaptive Cointelligence.cmd. Windows 10/11 x64 is the target.',state='%LOCALAPPDATA%\\Adaptive Cointelligence Reviewer'))
    manifest(windows, dict(**meta, audience='business reviewer', platforms=['Windows x86_64'], runtimes={'windows-x64':windows_runtime}))
    archive(windows, output / 'AdaptiveCointelligence-Review-Windows.zip')
    (output / 'SHA256SUMS.txt').write_text(''.join(digest(p)+'  '+p.name+'\n' for p in sorted(output.glob('*.zip'))))
    print(json.dumps(dict(commit=commit,archives=[dict(name=p.name,bytes=p.stat().st_size,sha256=digest(p)) for p in sorted(output.glob('*.zip'))]),indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-cache',type=Path,required=True)
    parser.add_argument('--wheelhouse',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    build(args.runtime_cache.resolve(),args.wheelhouse.resolve(),args.output.resolve())
