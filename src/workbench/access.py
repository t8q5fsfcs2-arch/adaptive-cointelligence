"""Local account adapter. Project records retain their existing actor identities.

This is loopback-only account authentication, not enterprise SSO. One account
binds to one existing actor; membership never follows a client-posted role.
"""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import threading
import time
from uuid import uuid4

from .decisions import ACTORS, ADMIN_ACTOR


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def password_hash(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**17,
                          r=8, p=1, maxmem=256*1024*1024, dklen=32).hex()


class Access:
    def __init__(self, anchor):
        anchor = Path(anchor).resolve()
        self.path = anchor.with_name(anchor.stem + '-access.sqlite3')
        self.setup_file = anchor.with_name(anchor.stem + '-account-setup.txt')
        self.lock = threading.RLock()
        if not self.path.exists():
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        os.chmod(self.path, 0o600)
        with self.db() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    actor TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, hash TEXT NOT NULL,
                    admin INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS portfolio_visibility (
                    account TEXT NOT NULL, project TEXT NOT NULL,
                    PRIMARY KEY(account,project));
                CREATE TABLE IF NOT EXISTS memberships (
                    account TEXT NOT NULL, project TEXT NOT NULL,
                    PRIMARY KEY(account,project));
                CREATE TABLE IF NOT EXISTS invitations (
                    hash TEXT PRIMARY KEY, actor TEXT NOT NULL, project TEXT,
                    expires REAL NOT NULL, bootstrap INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS failures (
                    username TEXT PRIMARY KEY, count INTEGER NOT NULL, until REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS access_audit (
                    at REAL NOT NULL, account TEXT, action TEXT NOT NULL,
                    subject TEXT, project TEXT);
            ''')
        # Separate legacy combined sponsor/admin identity without changing its
        # credentials, authored records, project memberships or conversation owner.
        with self.db() as db:
            legacy=db.execute('SELECT id FROM accounts WHERE actor=? AND admin=1',('priya',)).fetchone()
            if legacy and not db.execute('SELECT 1 FROM accounts WHERE actor=?',(ADMIN_ACTOR,)).fetchone():
                db.execute('UPDATE accounts SET actor=? WHERE id=?',(ADMIN_ACTOR,legacy['id']))
                db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),legacy['id'],'separate-admin-persona',ADMIN_ACTOR,None))
            db.execute('UPDATE invitations SET actor=? WHERE bootstrap=1',(ADMIN_ACTOR,))
        # Constant-cost unknown-account verification; never an actual password.
        self.dummy_salt = secrets.token_hex(16)
        self.dummy_hash = password_hash(secrets.token_urlsafe(32), self.dummy_salt)

    @contextmanager
    def db(self):
        with self.lock:
            db = sqlite3.connect(self.path)
            db.row_factory = sqlite3.Row
            try:
                with db:
                    yield db
            finally:
                db.close()

    def setup_needed(self):
        with self.db() as db:
            return db.execute('SELECT count(*) FROM accounts').fetchone()[0] == 0

    def bootstrap(self, url):
        with self.db() as db:
            if db.execute('SELECT count(*) FROM accounts').fetchone()[0]:
                return None
            valid = db.execute('SELECT 1 FROM invitations WHERE bootstrap=1 AND expires>?', (time.time(),)).fetchone()
            if valid and self.setup_file.exists():
                return self.setup_file
            db.execute('DELETE FROM invitations WHERE bootstrap=1')
            token = secrets.token_urlsafe(32)
            db.execute('INSERT INTO invitations VALUES (?,?,?,?,1)', (digest(token),ADMIN_ACTOR,None,time.time()+86400))
            fd = os.open(self.setup_file, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
            os.chmod(self.setup_file,0o600)
            with os.fdopen(fd,'w') as stream:
                stream.write('Create the local administrator account (expires in 24 hours):\n'+url+'/#enroll='+token+'\n')
        return self.setup_file

    @staticmethod
    def public(row):
        return {k:row[k] for k in ('id','username','actor','admin')} if row else None

    def account(self, account_id):
        with self.db() as db:
            return self.public(db.execute('SELECT * FROM accounts WHERE id=?',(account_id,)).fetchone())

    def allowed(self, account, project):
        with self.db() as db:
            return bool(db.execute('SELECT 1 FROM memberships WHERE account=? AND project=?',(account['id'],project)).fetchone())

    def projects(self, account):
        with self.db() as db:
            return {r[0] for r in db.execute('SELECT project FROM memberships WHERE account=?',(account['id'],))}

    def portfolio_projects(self,account):
        with self.db() as db:return {r[0] for r in db.execute('SELECT project FROM portfolio_visibility WHERE account=?',(account['id'],))}

    def portfolio_configuration(self,account,projects):
        if not account['admin']:raise PermissionError('Only an administrator can manage portfolio visibility.')
        with self.db() as db:
            users=[dict(id=r['id'],username=r['username'],actor=r['actor'],projects=[p[0] for p in db.execute('SELECT project FROM portfolio_visibility WHERE account=?',(r['id'],))]) for r in db.execute('SELECT id,username,actor FROM accounts ORDER BY username')]
        for user in users:user['basis']=digest(json.dumps(sorted(user['projects'])))
        return dict(accounts=users,projects=projects)

    def save_portfolio_visibility(self,account,data,valid_ids):
        if not account['admin']:raise PermissionError('Only an administrator can manage portfolio visibility.')
        subject=data.get('account');ids=data.get('projects')
        if not isinstance(ids,list) or len(ids)>500 or any(not isinstance(p,str) for p in ids) or len(set(ids))!=len(ids) or not set(ids)<=set(valid_ids):raise ValueError('Choose registered projects from the portfolio access list.')
        with self.db() as db:
            if not db.execute('SELECT 1 FROM accounts WHERE id=?',(subject,)).fetchone():raise ValueError('Choose an existing account.')
            current=[r[0] for r in db.execute('SELECT project FROM portfolio_visibility WHERE account=?',(subject,))]
            if data.get('expected')!=digest(json.dumps(sorted(current))):raise ValueError('Portfolio visibility changed. Reopen this setting before saving.')
            db.execute('DELETE FROM portfolio_visibility WHERE account=?',(subject,))
            db.executemany('INSERT INTO portfolio_visibility VALUES (?,?)',[(subject,p) for p in ids])
            db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),account['id'],'portfolio-visibility',subject,json.dumps(sorted(ids))))
        return dict(message='Portfolio visibility saved. Project membership and administrative permissions are unchanged.')

    def grant(self, account, project, by):
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO memberships VALUES (?,?)',(account,project))
            db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),by,'grant',account,project))

    def enroll(self, token, username, password, projects):
        username = str(username).strip().lower()
        if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,63}', username):
            raise ValueError('Use 3–64 letters, numbers, dots, hyphens or underscores for the username.')
        if not isinstance(password,str) or not 15 <= len(password) <= 128:
            raise ValueError('Use a password or passphrase of 15–128 characters.')
        with self.db() as db:
            invitation = db.execute('SELECT * FROM invitations WHERE hash=? AND expires>?',(digest(str(token)),time.time())).fetchone()
            if not invitation:
                raise ValueError('This setup link is invalid or expired. Request a new link from your administrator.')
            if invitation['bootstrap'] and db.execute('SELECT count(*) FROM accounts').fetchone()[0]:
                raise ValueError('Administrator setup is already complete.')
            if db.execute('SELECT 1 FROM accounts WHERE username=? OR actor=?',(username,invitation['actor'])).fetchone():
                raise ValueError('This username or member already has an account.')
            salt=secrets.token_hex(16); hashed=password_hash(password,salt); id=uuid4().hex
            db.execute('INSERT INTO accounts VALUES (?,?,?,?,?,?)',(id,username,invitation['actor'],salt,hashed,invitation['bootstrap']))
            destinations=[] if invitation['bootstrap'] else [invitation['project']]
            for project in destinations:
                db.execute('INSERT INTO memberships VALUES (?,?)',(id,project))
            db.execute('DELETE FROM invitations WHERE actor=?',(invitation['actor'],))
            db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),id,'enroll',invitation['actor'],invitation['project']))
        if invitation['bootstrap']:
            self.setup_file.unlink(missing_ok=True)
        return self.account(id)

    def login(self, username, password):
        username=str(username).strip().lower()[:64]
        with self.db() as db:
            failure=db.execute('SELECT * FROM failures WHERE username=?',(username,)).fetchone()
            if failure and failure['count']>=5 and failure['until']>time.time():
                raise PermissionError('Sign-in temporarily unavailable. Try again in 15 minutes.')
            row=db.execute('SELECT * FROM accounts WHERE username=?',(username,)).fetchone()
            supplied=password if isinstance(password,str) and len(password)<=128 else ''
            valid=hmac.compare_digest(password_hash(supplied,row['salt'] if row else self.dummy_salt),row['hash'] if row else self.dummy_hash)
            if row and valid:
                db.execute('DELETE FROM failures WHERE username=?',(username,))
                db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),row['id'],'login',None,None))
                result=self.public(row)
            else:
                count=failure['count']+1 if failure and failure['until']>time.time() else 1
                db.execute('INSERT OR REPLACE INTO failures VALUES (?,?,?)',(username,count,time.time()+900))
                result=None
        if not result:
            raise PermissionError('Username or password was not recognized.')
        return result

    def members(self, account, project):
        if not account['admin']:
            raise PermissionError('Administrator access is required.')
        with self.db() as db:
            rows=db.execute('SELECT a.id,a.actor,a.username,a.admin FROM accounts a JOIN memberships m ON m.account=a.id WHERE m.project=?',(project,)).fetchall()
            invites=db.execute('SELECT actor,expires FROM invitations WHERE project=? AND expires>?',(project,time.time())).fetchall()
            return dict(members=[dict(r) for r in rows],invitations=[dict(r) for r in invites])

    def invite(self, account, project, actor):
        self.members(account,project)
        if actor not in ACTORS:
            raise ValueError('Choose an existing sponsor, Research, Design, requirement-owner or legacy reviewer identity.')
        with self.db() as db:
            existing=db.execute('SELECT id FROM accounts WHERE actor=?',(actor,)).fetchone()
            if existing:
                self.grant(existing['id'],project,account['id'])
                return dict(message='Existing account granted access to this project.')
            token=secrets.token_urlsafe(32)
            db.execute('DELETE FROM invitations WHERE actor=?',(actor,))
            db.execute('INSERT INTO invitations VALUES (?,?,?,?,0)',(digest(token),actor,project,time.time()+86400))
            db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),account['id'],'invite',actor,project))
            return dict(message='Account setup link created. It expires in 24 hours.',token=token)

    def revoke(self, account, project, target):
        self.members(account,project)
        if target==account['id']:
            raise ValueError('You cannot remove your own administrator access.')
        with self.db() as db:
            db.execute('DELETE FROM memberships WHERE account=? AND project=?',(target,project))
            db.execute('INSERT INTO access_audit VALUES (?,?,?,?,?)',(time.time(),account['id'],'revoke',target,project))
        return dict(message='Project access removed. Saved work remains intact.')
