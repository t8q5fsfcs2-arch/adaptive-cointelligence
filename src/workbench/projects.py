"""Local project catalog; each project retains its own versioned SQLite store.

Reset/restore replace a catalog pointer, never delete the predecessor. Files are
created completely before the pointer transaction commits. Browser writes name
both the project and its generation so stale tabs cannot write into a reset.
"""
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
import json
import sqlite3
import threading
from uuid import uuid4

from .core import Store, StaleBasis
from .decisions import now, SCOPE
from .intake import Intake, PRIVATE
from .validation import required


class Projects:
    def __init__(self, anchor):
        self.anchor = Path(anchor).resolve()
        self.catalog = self.anchor.with_name(self.anchor.stem + '-projects.sqlite3')
        self.directory = self.anchor.with_name(self.anchor.stem + '-projects')
        self._locks = {}
        self._lock_guard = threading.Lock()
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, path TEXT NOT NULL UNIQUE,
                    version INTEGER NOT NULL, created_at TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS project_references (
                    number INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id TEXT NOT NULL UNIQUE REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS project_connections (
                    source_key TEXT NOT NULL, source_id TEXT NOT NULL, target_id TEXT NOT NULL UNIQUE,
                    label TEXT NOT NULL, source_generation INTEGER NOT NULL, source_digest TEXT NOT NULL,
                    connected_at TEXT NOT NULL, PRIMARY KEY(source_key,source_id),
                    FOREIGN KEY(target_id) REFERENCES projects(id));
                CREATE TABLE IF NOT EXISTS saved_versions (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
                    path TEXT NOT NULL, reason TEXT NOT NULL, saved_at TEXT NOT NULL,
                    FOREIGN KEY(project_id) REFERENCES projects(id));
            ''')
            db.execute('INSERT OR IGNORE INTO projects VALUES (?,?,?,?)',
                       ('original', str(self.anchor), 1, now()))
            db.execute('''INSERT INTO project_references(project_id)
                SELECT p.id FROM projects p WHERE NOT EXISTS
                (SELECT 1 FROM project_references r WHERE r.project_id=p.id)
                ORDER BY p.created_at,p.id''')

    @staticmethod
    def assign_reference(db, project_id):
        db.execute("INSERT INTO project_references(project_id) SELECT ? WHERE NOT EXISTS (SELECT 1 FROM project_references WHERE project_id=?)", (project_id,project_id))

    @contextmanager
    def db(self):
        db = sqlite3.connect(self.catalog)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def current(self, project_id, version=None):
        with self.db() as db:
            row = db.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            raise ValueError('Project not found. Reopen the project picker.')
        project = dict(row)
        if version is not None and str(project['version']) != str(version):
            raise StaleBasis('This project was reset or restored in another tab. Reload before saving; your unsaved text is still here.')
        if not Path(project['path']).is_file():
            raise sqlite3.OperationalError('Project database is missing')
        return project

    @contextmanager
    def locked(self, project_id, version=None):
        with self._lock_guard:
            lock = self._locks.setdefault(project_id, threading.RLock())
        with lock:
            yield self.current(project_id, version)

    def info(self, project, actor=None):
        # Read-only open must fail rather than silently create an empty database.
        db = sqlite3.connect(Path(project['path']).as_uri() + '?mode=ro', uri=True)
        try:
            row = db.execute("SELECT body FROM records WHERE id='PROJECT-001' ORDER BY revision DESC LIMIT 1").fetchone()
            title = json.loads(row[0]).get('title', '') if row else ''
            summary = self.sponsor_summary(db, project) if actor == 'priya' else None
        finally:
            db.close()
        with self.db() as catalog:
            number=catalog.execute('SELECT number FROM project_references WHERE project_id=?',(project['id'],)).fetchone()
            if not number:raise ValueError('Project reference unavailable. Reopen the project catalog.')
            reference=f"WB-{number['number']:03d}"
            connection=catalog.execute('SELECT label,connected_at FROM project_connections WHERE target_id=?',(project['id'],)).fetchone()
        return {'reference':reference, 'version_label':f"v{project['version']}",
                'display_title':f"{reference} · v{project['version']} — {title or 'Untitled project'}",
                'origin':connection['label'] if connection else '', 'connected_at':connection['connected_at'] if connection else None, 'id': project['id'], 'version': project['version'],
                'title': title or 'Untitled project', 'created_at': project['created_at'], **({'summary': summary} if summary is not None else {})}

    @staticmethod
    def sponsor_summary(db, project):
        """Bounded read-only metadata, never source/answer text or private domain work."""
        from .decisions import SCOPE
        rows = db.execute("""SELECT r.id,r.revision,r.kind,r.body FROM records r
            JOIN (SELECT id,MAX(revision) revision FROM records GROUP BY id) v
            ON r.id=v.id AND r.revision=v.revision WHERE r.scope IN (?,?) AND r.kind IN ('project','intent','intake-draft','intake-case','intent-decision','bridge-issue','decision','goal','success-measure','contribution')""", (SCOPE, PRIVATE)).fetchall()
        records = {r[0]: dict(revision=r[1], kind=r[2], body=json.loads(r[3])) for r in rows}
        draft = records.get('INTAKE-001', {}).get('body', {})
        intent = records.get('INT-001')
        cases = [r for r in records.values() if r['kind'] == 'intake-case']
        pending = [r for r in cases if r['body'].get('status') == 'pending-review']
        values = draft.get('values', {})
        entered = any(isinstance(v, str) and v.strip() for k,v in values.items() if k not in {'work_kind','assumption_owner'})
        stage = 'Project dashboard' if intent else 'Review & publish' if pending else 'Requirements' if draft.get('scaffold') else 'Business Intent' if entered else 'Context'
        needs = []
        if pending: needs.append('Direction review open')
        if intent and values and values != intent['body'].get('intake', {}): needs.append('Unpublished changes')
        issues = sum(r['kind'] == 'bridge-issue' and r['body'].get('status') != 'resolved' for r in records.values())
        if issues: needs.append(str(issues) + (' open issue' if issues == 1 else ' open issues'))
        if not intent and not pending: needs.append('Continue your brief' if entered else 'Start your brief')
        activity = project['created_at']
        for r in records.values():
            for key in ('at','saved_at','created_at','published_at'):
                value = r['body'].get(key)
                if isinstance(value, str) and value > activity: activity = value
        decision = records.get(intent['body'].get('decision_id'), {}).get('body', {}) if intent else {}
        return dict(stage=stage, brief_status='published' if intent else 'draft' if draft else 'not-started',
                    brief_revision=intent['revision'] if intent else None,
                    published_at=decision.get('at'), needs=needs, last_activity=activity,
                    source_count=db.execute("SELECT COUNT(DISTINCT id) FROM records WHERE kind='intake-source' AND scope=?", (PRIVATE,)).fetchone()[0])

    def listing(self, actor=None, allowed_ids=None):
        with self.db() as db:
            projects = [dict(row) for row in db.execute('SELECT * FROM projects ORDER BY created_at,id')]
        # Membership filtering precedes opening project stores and preparing sponsor metadata.
        if allowed_ids is not None:
            projects = [p for p in projects if p['id'] in allowed_ids]
        return [self.info(project, actor) for project in projects]

    def history(self, project_id):
        with self.db() as db:
            return [dict(row) for row in db.execute(
                'SELECT id,reason,saved_at FROM saved_versions WHERE project_id=? ORDER BY rowid DESC', (project_id,))]

    @staticmethod
    def sponsor(actor):
        if actor != 'priya':
            raise PermissionError('Use the Business sponsor profile to create, reset or restore a project.')

    def new_path(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory / (uuid4().hex + '.sqlite3')

    def empty_intake(self, title):
        path = self.new_path()
        store = Store(path)
        try:
            Intake(store, 'priya').start({'title': title})
            from .setup_governance import enable
            project = store.latest('PROJECT-001', {SCOPE})
            enable(store, 'priya', {'expected': asdict(project['ref']), 'confirm': True})
        finally:
            store.close()
        return path

    def create(self, data, actor):
        self.sponsor(actor)
        title = required(data, 'title')
        if len(title) > 200:
            raise ValueError('Keep the project name to 200 characters or fewer.')
        path = self.empty_intake(title)
        project_id = uuid4().hex
        with self.db() as db:
            db.execute('INSERT INTO projects VALUES (?,?,?,?)', (project_id, str(path), 1, now()))
            self.assign_reference(db,project_id)
        return {'project_id': project_id, 'message': 'New project created. Your other projects are saved.'}

    def replace(self, project, data, actor, restore=False):
        self.sponsor(actor)
        title = self.info(project)['title']
        if data.get('confirm_title') != title:
            raise ValueError('Enter the current project name to confirm.')
        if restore:
            with self.db() as db:
                saved = db.execute('SELECT * FROM saved_versions WHERE id=? AND project_id=?',
                                   (data.get('saved_version'), project['id'])).fetchone()
            if not saved:
                raise ValueError('Saved version not found for this project.')
            path = self.new_path()
            source = sqlite3.connect(Path(saved['path']).as_uri() + '?mode=ro', uri=True)
            target = sqlite3.connect(path)
            try:
                source.backup(target)
            finally:
                source.close()
                target.close()
        else:
            path = self.empty_intake(title)
        with self.db() as db:
            changed = db.execute('UPDATE projects SET path=?,version=version+1 WHERE id=? AND version=?',
                                 (str(path), project['id'], project['version'])).rowcount
            if changed != 1:
                raise StaleBasis('This project changed. Reopen it before trying again.')
            db.execute('INSERT INTO saved_versions VALUES (?,?,?,?,?)',
                       (uuid4().hex, project['id'], project['path'],
                        'Before restore' if restore else 'Before reset', now()))
        return {'project_id': project['id'], 'message': 'Saved version restored. Previous work is kept in Saved versions.' if restore
                else 'Project reset. Previous work is kept in Saved versions.'}
