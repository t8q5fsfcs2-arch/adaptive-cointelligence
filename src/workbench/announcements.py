"""Sitewide Home announcements, with separate drafts and exact publication snapshots.

Stored in the existing project catalog, never in a particular project's records.
The HTTP boundary establishes Admin authority; plain text is escaped by the UI.
"""
from copy import deepcopy
import json

from .core import StaleBasis
from .decisions import now

SAMPLE_ITEMS = [
    {'title': 'New: project connections', 'body': 'Manage model and tool setup from Settings, with configuration kept clear by project.'},
    {'title': 'Coming soon: quick tips', 'body': 'Short walkthroughs to help teams review documents and resolve shared decisions.'},
]
MAX_ITEMS = 3


class Announcements:
    def __init__(self, projects):
        self.projects = projects
        with projects.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS home_announcement_versions (
                revision INTEGER PRIMARY KEY, action TEXT NOT NULL CHECK(action IN ('draft','publish')),
                items TEXT NOT NULL, author TEXT NOT NULL, at TEXT NOT NULL, basis INTEGER)''')

    @staticmethod
    def record(row):
        return dict(revision=row['revision'], action=row['action'], items=json.loads(row['items']),
                    author=json.loads(row['author']), at=row['at'], basis=row['basis']) if row else None

    @staticmethod
    def validate(items):
        if not isinstance(items, list) or len(items) > MAX_ITEMS:
            raise ValueError('Use up to three announcements. An empty list clears the Home announcement area when published.')
        clean = []
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Provide an announcement title and message.')
            entry = {}
            for key, limit in (('title', 100), ('body', 500)):
                value = item.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > limit:
                    raise ValueError(f'Each announcement needs a {key} of 1–{limit} characters.')
                if any((ord(c) < 32 and c not in ('\n', '\r', '\t')) or ord(c) == 127 for c in value):
                    raise ValueError('Remove control characters from the announcement.')
                if key == 'title' and any(c in value for c in '\n\r\t'):
                    raise ValueError('Keep the announcement title on one line.')
                entry[key] = value.strip()
            clean.append(entry)
        return clean

    @staticmethod
    def expected(data, latest):
        expected = data.get('expected')
        if type(expected) is not int or expected != (latest['revision'] if latest else 0):
            raise StaleBasis('Announcements changed in another session. Reopen Settings before saving or publishing. Your unsaved text remains in this form.')
        return expected

    def public(self):
        with self.projects.db() as db:
            row = db.execute("SELECT items,at FROM home_announcement_versions WHERE action='publish' ORDER BY revision DESC LIMIT 1").fetchone()
        return dict(items=json.loads(row['items']), sample=False, published_at=row['at']) if row else dict(items=deepcopy(SAMPLE_ITEMS), sample=True, published_at=None)

    def state(self):
        with self.projects.db() as db:
            latest = self.record(db.execute('SELECT * FROM home_announcement_versions ORDER BY revision DESC LIMIT 1').fetchone())
            history = [self.record(r) for r in db.execute("SELECT * FROM home_announcement_versions WHERE action='publish' ORDER BY revision DESC LIMIT 10")]
        published = history[0] if history else None
        return dict(revision=latest['revision'] if latest else 0,
                    items=latest['items'] if latest else deepcopy(SAMPLE_ITEMS),
                    draft=latest if latest and latest['action']=='draft' else None,
                    published=published, history=history,
                    pending=bool(latest and latest['action']=='draft' and (not published or latest['items']!=published['items'])))

    def save(self, data, author):
        items = self.validate(data.get('items'))
        with self.projects.db() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT * FROM home_announcement_versions ORDER BY revision DESC LIMIT 1').fetchone()
            revision = self.expected(data, latest)
            if not latest or json.loads(latest['items']) != items:
                db.execute('INSERT INTO home_announcement_versions VALUES (?,?,?,?,?,?)',
                           (revision+1, 'draft', json.dumps(items), json.dumps(author), now(), revision or None))
        return dict(message='Draft saved. Published announcements stay unchanged.')

    def publish(self, data, author):
        if data.get('confirm') is not True:
            raise ValueError('Preview the saved draft and explicitly publish it to Home.')
        with self.projects.db() as db:
            db.execute('BEGIN IMMEDIATE')
            latest = db.execute('SELECT * FROM home_announcement_versions ORDER BY revision DESC LIMIT 1').fetchone()
            # A retried exact publish returns the existing result, rather than duplicating it.
            if latest and latest['action']=='publish' and type(data.get('expected')) is int and latest['basis']==data['expected']:
                return dict(message='This version is already published on Home.')
            revision = self.expected(data, latest)
            if not latest or latest['action']!='draft':
                raise ValueError('Save a draft before publishing.')
            published = db.execute("SELECT items FROM home_announcement_versions WHERE action='publish' ORDER BY revision DESC LIMIT 1").fetchone()
            if published and published['items']==latest['items']:
                raise ValueError('These announcements are already published. Edit the draft to make a change.')
            db.execute('INSERT INTO home_announcement_versions VALUES (?,?,?,?,?,?)',
                       (revision+1, 'publish', latest['items'], json.dumps(author), now(), revision))
        return dict(message='Announcements published to Home.')
