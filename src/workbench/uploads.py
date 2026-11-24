"""Private upload receipts. Retain originals without revising source evidence."""
import base64
import hashlib
from pathlib import Path
from .decisions import now


def upload_owner(actor, principal=None):
    return 'account:'+principal if principal else 'profile:'+actor


def retain_upload(store, ref, data, owner, source, *, visual=False):
    """Called inside the source transaction, after extraction and authorization."""
    raw=base64.b64decode(data['content'],validate=True) if 'content' in data else None
    if raw is not None and hashlib.sha256(raw).hexdigest()!=source['sha256']:
        raise ValueError('The original file does not match the extracted source.')
    store.db.execute('''CREATE TABLE IF NOT EXISTS user_uploads(
        owner TEXT NOT NULL,source_id TEXT NOT NULL,source_revision INTEGER NOT NULL,
        filename TEXT NOT NULL,at TEXT NOT NULL,sha256 TEXT NOT NULL,original BLOB,
        PRIMARY KEY(owner,source_id,source_revision),
        FOREIGN KEY(source_id,source_revision) REFERENCES records(id,revision))''')
    store.db.execute('INSERT OR IGNORE INTO user_uploads VALUES (?,?,?,?,?,?,?)',
        (owner,ref.id,ref.revision,Path(source['title']).name,now(),source['sha256'],
         None if visual else raw))
