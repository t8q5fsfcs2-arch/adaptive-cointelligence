# NorthStar review and developer packages

This release packages the existing local prototype, its UI, configuration and
implemented connector adapters. It changes distribution, not workflow authority,
semantic judgments or enterprise integration scope. Architecture §§4.1–4.2, 12.1,
19.1 and 19.3 and ADR0037 apply. Existing real workspaces are never imported,
reset or migrated. Paid calls, full-corpus processing and human simulation remain
on hold.

## Choose a package

| Recipient | Archive | Start |
|---|---|---|
| Business reviewer on Mac | `NorthStar-Review-macOS.zip` | Extract, then double-click `Open NorthStar.command`. Includes Apple Silicon and Intel Python runtimes. macOS12+ target. |
| Business reviewer on Windows | `NorthStar-Review-Windows.zip` | Extract the whole folder, then open `Open NorthStar.cmd`. Windows10/11 x64 target. |
| Developer | `NorthStar-Developer.zip` | Read `AGENTS.md`, this guide and the connector matrix; use Python3.12+. |

Reviewer packages include Python3.12.14, NetworkX3.7, pypdf6.21.4, local assets and
licenses. Internet and a Python installation are not required to start. They open
the same browser UI using fictional clinic data created through existing workflow
services. Existing example model/persona exchanges are explicitly scripted fixtures.
They are not a real human simulation or evidence of model quality.

The small console shows the browser link and workspace location. Keep it open
while reviewing. **Ctrl+C in the console** shuts down the local server; saved
records remain. Launching again resumes them. A system lock prevents concurrent launchers
on the same workspace. A free loopback port is selected at startup; browser-local
navigation/drafts can vary with the browser origin, while application records remain
in SQLite. Save entered work before stopping.

The reviewer launcher deliberately supplies `UnconfiguredModel` to every project.
It does not load inherited provider keys or model profiles; model-configuration and
connection-test endpoints are unavailable. The native source code remains included
for a developer's separately authorized integration work. Connector code does not
mean vendor credentials, live compatibility or external writes are enabled. See
[connector capabilities](CONNECTOR_CAPABILITIES.md).

These are private prototype distributions using command launchers rather than
signed installers or a notarized Mac app. Device
policy may require IT review. Windows ARM is not a native package target. Optional
PDF image review still requires Poppler (`pdftoppm`/`pdftotext`) plus separately
authorized vision processing; the pure-Python PDF text extractor is bundled.

## Saved work and isolation

- Mac: `~/Library/Application Support/NorthStar Reviewer`
- Windows: `%LOCALAPPDATA%\NorthStar Reviewer`
- Other developer environments: `~/.local/share/NorthStar Reviewer`

The command launcher opens the browser directly, without a separate desktop GUI
toolkit. A bundled-Tk control window was blank during native Mac inspection, so it
is not part of the reviewer experience. Both platforms use the same console-based
start/stop path. Mac hardware detection also avoids selecting an Intel runtime
merely because a script starts under Rosetta.

The package never scans for the author's data or imports an existing project.
Only an empty or previously marked demo directory is accepted. A fresh example uses
an explicitly new `--state-dir`; there is no automatic reset. Closing the launcher
does not remove work. Removing the downloaded app does not remove its data directory.
Back up the whole workspace while the app is stopped to preserve local records.

Development role switching is enabled for inspection. It is not enterprise sign-in,
SSO or a multi-user hosted deployment. Keep the demo local and use fictional inputs.
The known performance limitation on the author's much larger Research workspace
has not been established as resolved by packaging this smaller fixture.

## Developer startup

From the extracted developer directory, with Python3.12+:

```sh
python run_demo.py --offline --check
python run_demo.py --offline
```

On Mac/Linux, `python3` may be the appropriate executable; on Windows use `py -3.12`
if `python` is not your Python3.12+ command. The package wheelhouse supports offline,
hash-locked installation into `a local `venv` folder`. Normal source-clone startup can
omit `--offline` to fetch the same two pinned wheels. No system packages are changed.
The developer demo path permits explicit model setup through Admin settings; doing
so and requesting a model response can incur provider charges. That is separate
from this held, offline release task.

Checks use disposable databases. Runtime work is ignored by Git. Core verification:

```sh
python -m unittest discover -s tests -p 'test_reviewer_launcher.py' -v
python -m unittest discover -s tests -p 'test_release_package.py' -v
```

Use the demo virtual environment with `PYTHONPATH=src` for these source tests.
`scripts/test_offline.py` is the broader backend suite; `node --test tests/*.test.cjs`
checks UI contracts. Test results are structural/workflow evidence, not semantic
accuracy, usability or live vendor acceptance evidence.

## Rebuild and verify

To rebuild, use the Git repository on the recorded source commit; the ZIP is a
source handoff and intentionally has no `.git` history. `scripts/build_release.py`
requires a clean committed checkout, pinned runtime
archives in a runtime cache and the two locked wheels in a wheelhouse. It performs
no download and no model call. It checks SHA256 before extraction, copies only
tracked source files, excludes historical model-result JSON under `docs/evaluation`,
and never traverses ignored/untracked workspaces or `.git`. Every artifact includes
a source commit, dependency/runtime provenance and a per-file manifest. Third-party
runtime and dependency licenses travel with their components. This handoff does
not create a new license grant for the application's independently owned source or
client assets.

Portable Python runtime source:
[Astral python-build-standalone release20260901](https://github.com/astral-sh/python-build-standalone/releases/tag/20260901).
The exact release, filenames and SHA256 are pinned in the build script. Download
only those assets and obtain the wheels with the repository's hash-locked
`requirements-demo.txt`, then run:

```sh
python scripts/build_release.py --runtime-cache /path/to/runtime-cache \
  --wheelhouse /path/to/wheelhouse --output /path/to/new-release-folder
```

`SHA256SUMS.txt` verifies the three ZIPs; `PACKAGE-MANIFEST.json` inside each verifies
its files (symlink targets are recorded separately). The manifest does not hash
itself. Native OS startup results and remaining limitations are recorded separately
in the release verification note. Included binaries and source completeness do not
imply that all OSes or connectors have received live acceptance testing.
