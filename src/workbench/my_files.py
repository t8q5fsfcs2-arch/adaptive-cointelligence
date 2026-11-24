"""Owner-private file inventory and organization over existing, permissioned stores.

Project sources and conversation documents remain in their original stores. The
sidecar contains personal display names/archive preferences, never source copies.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import sqlite3

from .core import Store, Ref, StaleBasis
from .decisions import SCOPE, now
from .domain import configured_domains
from .intake import PRIVATE


class ReadStore:
    read=Store.read
    def __init__(self,db):self.db=db


@contextmanager
def readonly(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:yield db
    finally:db.close()


def has_table(db,name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())


def identifier(*parts):
    return hashlib.sha256(json.dumps(parts,separators=(',',':')).encode()).hexdigest()


class MyFiles:
    def __init__(self,anchor,projects,chat):
        self.projects,self.chat=projects,chat
        p=Path(anchor);self.path=p.with_name(p.stem+'-files.sqlite3')
        if not self.path.exists():
            fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
        with self.db() as db:
            db.executescript('''CREATE TABLE IF NOT EXISTS file_preferences(
                owner TEXT NOT NULL,id TEXT NOT NULL,title TEXT,archived INTEGER NOT NULL,
                revision INTEGER NOT NULL,PRIMARY KEY(owner,id));
                CREATE TABLE IF NOT EXISTS file_preference_history(
                owner TEXT NOT NULL,id TEXT NOT NULL,revision INTEGER NOT NULL,
                action TEXT NOT NULL,title TEXT,archived INTEGER NOT NULL,at TEXT NOT NULL,
                PRIMARY KEY(owner,id,revision));''')
        self.path.chmod(0o600)

    @contextmanager
    def db(self):
        db=sqlite3.connect(self.path,timeout=10);db.row_factory=sqlite3.Row
        try:
            with db:yield db
        finally:db.close()

    def _project_files(self,owner,actor,allowed):
        files={};unavailable=0
        # Filter membership before opening any project store, even for admins.
        with self.projects.db() as catalog:
            projects=[dict(p) for p in catalog.execute('SELECT * FROM projects') if p['id'] in allowed]
        for project in projects:
            try:
                info=self.projects.info(project)
                with readonly(project['path']) as current:
                    domains=configured_domains(ReadStore(current))
                scopes={d['scope']:key for key,d in domains.items() if actor in d['authors']}
                if actor=='priya':scopes[PRIVATE]='business'
                if actor=='maya':scopes['domain:operations']='operations'
                if not scopes:continue
                with self.projects.db() as catalog:
                    snapshots=[dict(p) for p in catalog.execute('SELECT id,path,saved_at FROM saved_versions WHERE project_id=? ORDER BY saved_at DESC',(project['id'],))]
                stores=[dict(id=None,path=project['path'],saved_at=None),*snapshots]
                for snapshot in stores:
                    with readonly(snapshot['path']) as db:
                        marks=','.join('?' for _ in scopes)
                        rows=db.execute(f'''SELECT r.id,r.revision,r.kind,r.scope,
                            json_extract(r.body,'$.title') title,
                            json_extract(r.body,'$.author') author,
                            json_extract(r.body,'$.owner') author_owner,
                            json_extract(r.body,'$.at') at,
                            json_extract(r.body,'$.sha256') sha,
                            json_extract(r.body,'$.parser') parser,
                            length(json_extract(r.body,'$.text')) characters
                            FROM records r WHERE r.kind IN ('source','intake-source')
                            AND r.scope IN ({marks}) ORDER BY r.revision DESC''',tuple(scopes))
                        for row in rows:
                            key=identifier('project',project['id'],row['id'],row['revision'])
                            if key in files:continue
                            receipts=[]
                            if has_table(db,'user_uploads'):
                                receipts=db.execute('SELECT owner,filename,at,length(original) original_bytes FROM user_uploads WHERE source_id=? AND source_revision=?',(row['id'],row['revision'])).fetchall()
                            receipt=next((r for r in receipts if r['owner']==owner),None)
                            if receipts and not receipt:continue
                            if not receipts and (row['author'] or row['author_owner'])!=actor:continue
                            original=bool(receipt and receipt['original_bytes'])
                            if has_table(db,'visual_pdf_files'):
                                original=original or bool(db.execute('SELECT 1 FROM visual_pdf_files WHERE source_id=? AND source_revision=?',(row['id'],row['revision'])).fetchone())
                            domain=scopes[row['scope']]
                            locations=[]
                            if domain!='business':
                                threads=db.execute("""SELECT r.id,json_extract(r.body,'$.draft_id') draft_id FROM records r
                                    JOIN (SELECT id,MAX(revision) revision FROM records WHERE kind='domain-conversation' GROUP BY id) latest
                                    ON r.id=latest.id AND r.revision=latest.revision
                                    WHERE r.scope=? AND json_extract(r.body,'$.owner')=?""",(row['scope'],actor))
                                for thread in threads:
                                    draft=db.execute('SELECT body FROM records WHERE id=? ORDER BY revision DESC LIMIT 1',(thread['draft_id'],)).fetchone()
                                    if draft:
                                        body=json.loads(draft['body'])
                                        if dict(id=row['id'],revision=row['revision']) in body.get('source_refs',[]):
                                            locations.append(dict(kind='domain',id=thread['id'],draft=thread['draft_id'],domain=domain,title=body.get('title') or 'Domain conversation'))
                            filename=receipt['filename'] if receipt else row['title'] or 'Untitled upload'
                            files[key]=dict(id=key,kind='project',title=filename,filename=filename,
                                at=receipt['at'] if receipt else row['at'],characters=row['characters'] or 0,
                                original_available=original,parser=row['parser'] or 'Earlier extraction',
                                ownership='recorded-upload' if receipt else 'earlier-role-upload',
                                project=project['id'],project_title=info['title'],project_reference=info['reference'],
                                project_display_title=(info['reference']+' — '+info['title']) if snapshot['id'] else info['display_title'],origin=info['origin'],
                                projects=[project['id']],domain=domain,
                                area='Business Intent' if domain=='business' else domains.get(domain,{}).get('label',domain.title()),
                                locations=locations,saved_version=snapshot['id'],saved_at=snapshot['saved_at'],
                                source=dict(id=row['id'],revision=row['revision']),source_archived=False,
                                _path=snapshot['path'],_sha=row['sha'],_scope=row['scope'])
            except (sqlite3.Error,OSError,ValueError):
                unavailable+=1
        return list(files.values()),unavailable

    def _thread_files(self,owner,allowed):
        result=[]
        with self.chat.db() as db:
            for thread in db.execute('SELECT id,title,projects FROM threads WHERE owner=?',(owner,)):
                if self.chat.blocked(db,thread['id'],allowed):continue
                projects=[p for p in json.loads(thread['projects']) if p in allowed]
                for row in db.execute("""SELECT id,title,at,archived_at,revision,
                        json_extract(body,'$.title') filename,json_extract(body,'$.parser') parser,
                        length(json_extract(body,'$.text')) characters
                        FROM documents WHERE thread=?""",(thread['id'],)):
                    result.append(dict(id=identifier('chat',thread['id'],row['id']),kind='conversation',
                        title=row['title'],filename=row['filename'] or row['title'],at=row['at'],
                        parser=row['parser'],characters=row['characters'],original_available=True,
                        ownership='recorded-upload',project=None,project_title='',origin='',projects=projects,
                        domain=None,area='AI partner',locations=[dict(kind='conversation',id=thread['id'],title=thread['title'])],
                        saved_version=None,saved_at=None,source=None,source_archived=bool(row['archived_at']),
                        _thread=thread['id'],_document=row['id']))
        return result

    def candidates(self,owner,actor,allowed):
        files,unavailable=self._project_files(owner,actor,allowed)
        files+=self._thread_files(owner,allowed)
        with self.db() as db:
            preferences={r['id']:dict(r) for r in db.execute('SELECT * FROM file_preferences WHERE owner=?',(owner,))}
        for item in files:
            pref=preferences.get(item['id'],{})
            item.update(title=pref.get('title') or item['title'],archived=bool(pref.get('archived')),revision=pref.get('revision',0))
        return sorted(files,key=lambda f:(f['at'] or '',f['id']),reverse=True),unavailable

    @staticmethod
    def public(item):
        return {k:v for k,v in item.items() if not k.startswith('_')}

    def listing(self,owner,actor,allowed):
        files,unavailable=self.candidates(owner,actor,allowed)
        projects={p['id']:p for p in self.projects.listing(allowed_ids=allowed)}
        return dict(files=[self.public(f) for f in files],
            projects=[dict(id=p['id'],title=p['title'],reference=p['reference'],display_title=p['display_title']) for p in projects.values() if any(p['id'] in f['projects'] for f in files)],
            unavailable_locations=unavailable)

    def resolve(self,owner,actor,allowed,id):
        files,_=self.candidates(owner,actor,allowed)
        item=next((f for f in files if f['id']==id),None)
        if not item:raise PermissionError('This file is not available in your library.')
        return item

    def detail(self,owner,actor,allowed,id):
        item=self.resolve(owner,actor,allowed,id)
        if item['kind']=='conversation':
            body=self.chat.document(owner,allowed,item['_thread'],item['_document'])
        else:
            with readonly(item['_path']) as db:
                row=db.execute('SELECT body FROM records WHERE id=? AND revision=?',(item['source']['id'],item['source']['revision'])).fetchone()
                body=json.loads(row['body'])
        return {**self.public(item),'text':body.get('text','')}

    def download(self,owner,actor,allowed,id,format):
        item=self.resolve(owner,actor,allowed,id)
        if format=='text':
            detail=self.detail(owner,actor,allowed,id)
            return detail['text'].encode(),Path(item['filename']).stem+'.txt','text/plain; charset=utf-8'
        if format!='original':raise ValueError('Choose the original file or extracted text.')
        if not item['original_available']:raise ValueError('This earlier upload retained extracted text only.')
        if item['kind']=='conversation':
            raw=self.chat.download_document(owner,allowed,item['_thread'],item['_document'])
            expected=self.chat.document(owner,allowed,item['_thread'],item['_document'])['sha256']
        else:
            with readonly(item['_path']) as db:
                row=db.execute('SELECT original,sha256 FROM user_uploads WHERE owner=? AND source_id=? AND source_revision=?',(owner,item['source']['id'],item['source']['revision'])).fetchone() if has_table(db,'user_uploads') else None
                if not row or row['original'] is None:
                    row=db.execute('SELECT content original,sha256 FROM visual_pdf_files WHERE source_id=? AND source_revision=?',(item['source']['id'],item['source']['revision'])).fetchone()
                raw=bytes(row['original']);expected=row['sha256']
                if expected!=item['_sha']:raise ValueError('The retained original failed its integrity check.')
        if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('The retained original failed its integrity check.')
        return raw,item['filename'],'application/octet-stream'

    def update(self,owner,actor,allowed,data):
        item=self.resolve(owner,actor,allowed,data.get('id'))
        action=data.get('action');title=item['title'];archived=item['archived']
        if action=='rename':
            title=data.get('title')
            if not isinstance(title,str) or not title.strip() or len(title)>200 or any(ord(c)<32 for c in title):
                raise ValueError('Use a display name of 1–200 characters.')
            title=title.strip()
        elif action=='archive':archived=True
        elif action=='restore':archived=False
        else:raise ValueError('Choose Rename, Archive or Restore.')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            current=db.execute('SELECT revision FROM file_preferences WHERE owner=? AND id=?',(owner,item['id'])).fetchone()
            revision=current['revision'] if current else 0
            if type(data.get('expected_revision')) is not int or data['expected_revision']!=revision:
                raise StaleBasis('This file changed. Refresh My files before saving.')
            revision+=1
            db.execute('INSERT OR REPLACE INTO file_preferences VALUES (?,?,?,?,?)',(owner,item['id'],title,int(archived),revision))
            db.execute('INSERT INTO file_preference_history VALUES (?,?,?,?,?,?,?)',(owner,item['id'],revision,action,title,int(archived),now()))
        return dict(message='File library updated. Project evidence and conversation attachments are unchanged.')
