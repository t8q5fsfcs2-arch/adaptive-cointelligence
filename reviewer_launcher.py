#!/usr/bin/env python3
"""Start an isolated fictional Adaptive Cointelligence review with paid model calls disabled."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import signal
import sys
import threading
import webbrowser

# Bundled runtimes use -I, which intentionally omits the script directory and
# PYTHONPATH. Resolve only this package's source and vendored dependencies.
ROOT = Path(__file__).resolve().parent
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'vendor'), str(ROOT)]

from run_demo import demo_lock, state_directory
from workbench.demo_package import initialize, workflow_check
from workbench.model_provider import UnconfiguredModel
from workbench.web import BrowserServer


NOTICE = 'Fictional reviewer workspace · AI model calls disabled · Jira/ADO simulated'


def default_state_directory(*, platform=None, home=None, environment=None):
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else Path(home)
    environment = os.environ if environment is None else environment
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / 'Adaptive Cointelligence Reviewer'
    if platform == 'win32' and environment.get('LOCALAPPDATA'):
        return Path(environment['LOCALAPPDATA']) / 'Adaptive Cointelligence Reviewer'
    return home / '.local' / 'share' / 'Adaptive Cointelligence Reviewer'


class ReviewerController:
    """Own one managed directory, loopback server and clean shutdown lifecycle."""

    def __init__(self, state_dir=None, port=0):
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError('Choose a port from 0 to 65535; 0 selects an available port.')
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_directory()
        self.port = port
        self.database = None
        self.server = None
        self.thread = None
        self._ownership = None
        self._lifecycle = threading.RLock()

    @property
    def url(self):
        return f'http://127.0.0.1:{self.server.server_port}/' if self.server else None

    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive())

    def start(self):
        with self._lifecycle:
            if self.running:
                return self
            ownership = ExitStack()
            server = None
            try:
                folder = state_directory(self.state_dir)
                ownership.enter_context(demo_lock(folder))
                database = folder / 'data' / 'workbench.sqlite3'
                initialize(database)
                # No ModelConnections manager: every request keeps this fixed
                # adapter, and model setup/test/assignment endpoints reject edits.
                server = BrowserServer(('127.0.0.1', self.port), database,
                                       UnconfiguredModel(), development=True,
                                       workspace_notice=NOTICE)
                thread = threading.Thread(target=server.serve_forever,
                                          kwargs={'poll_interval': 0.1},
                                          name='AdaptiveCointelligenceReviewerServer', daemon=True)
                thread.start()
            except BaseException:
                if server is not None:
                    server.server_close()
                ownership.close()
                raise
            self.state_dir = folder
            self.database = database
            self.server, self.thread, self._ownership = server, thread, ownership
            return self

    def open_workbench(self):
        if not self.running:
            raise ValueError('Start the reviewer before opening the workbench.')
        return webbrowser.open(self.url, new=2)

    def stop(self):
        with self._lifecycle:
            if self.server is None:
                return
            server, thread, ownership = self.server, self.thread, self._ownership
            try:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
                if thread.is_alive():
                    raise RuntimeError('The reviewer server did not finish stopping.')
            finally:
                self.server = self.thread = self._ownership = None
                ownership.close()


def run_headless(controller, *, open_browser=True):
    stopped = threading.Event()
    previous = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, lambda *_: stopped.set())
    try:
        if open_browser:
            controller.open_workbench()
        try:
            stopped.wait()
        except KeyboardInterrupt:
            pass
    finally:
        signal.signal(signal.SIGTERM, previous)
        controller.stop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-dir', type=Path, default=None, help='Managed saved-data directory')
    parser.add_argument('--port', type=int, default=0, help='Loopback port; 0 chooses an available port')
    parser.add_argument('--headless', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--no-browser', action='store_true', help='Do not automatically open the browser')
    parser.add_argument('--check', action='store_true', help='Check the existing fictional workflow in disposable data, then exit')
    args = parser.parse_args(argv)
    if sys.version_info < (3, 12):
        parser.exit(1, 'Adaptive Cointelligence Reviewer requires its bundled Python 3.12 or newer.\n')
    if not 0 <= args.port <= 65535:
        parser.error('Choose a port from 0 to 65535; 0 selects an available port.')
    controller = None
    try:
        if args.check:
            print(json.dumps(dict(status='passed', checks=workflow_check(),
                                  external_model_calls=0, external_writes=0), indent=2))
            return 0
        controller = ReviewerController(args.state_dir, args.port).start()
        print('\nAdaptive Cointelligence\n\nWorkbench: '+controller.url+
              '\nSaved reviewer work: '+str(controller.state_dir)+
              '\n\nFictional starting data. AI model calls are disabled.\nKeep this window open while reviewing.\nPress Ctrl+C here to stop; launch again to resume saved work.\n', flush=True)
        run_headless(controller, open_browser=not args.no_browser)
        print('Stopped. Your saved reviewer work remains available.', flush=True)
        return 0
    except KeyboardInterrupt:
        return 0
    except (ImportError, OSError, ValueError, RuntimeError) as error:
        print('Could not start Adaptive Cointelligence Reviewer: '+str(error), file=sys.stderr)
        print('Saved data was not reset. Close the other launcher or choose a new --state-dir if needed.', file=sys.stderr)
        return 1
    finally:
        if controller is not None:
            controller.stop()


if __name__ == '__main__':
    raise SystemExit(main())
