"""Explicit private upload routing. No model requests, publication or writeback."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from .core import Store, StaleBasis
from .decisions import fingerprint, now
from .domain import configured_domains
from .my_files import ReadStore, readonly, identifier
from .workspace import Workspace


def receipt_schema(db):
    db.execute('''CREATE TABLE IF NOT EXISTS file_upload_requests(
        owner TEXT NOT NULL,request_id TEXT NOT NULL,signature TEXT NOT NULL,
        result TEXT NOT NULL,at TEXT NOT NULL,PRIMARY KEY(owner,request_id))''')


def prior_receipt(db,owner,request,signature):
    row=db.execute('SELECT signature,result FROM file_upload_requests WHERE owner=? AND request_id=?',(owner,request)).fetchone()
    if row:
        if row['signature']!=signature:raise StaleBasis('This upload attempt has different contents or a different destination. Choose the file and destination again.')
        return json.loads(row['result'])


class FileUploads:
    def __init__(self,projects,chat,library,model):
        self.projects,self.chat,self.library,self.model=projects,chat,library,model
        with self.library.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS file_upload_attempts(
                owner TEXT NOT NULL,request_id TEXT NOT NULL,signature TEXT NOT NULL,
                at TEXT NOT NULL,PRIMARY KEY(owner,request_id))''')

    def reserve(self,owner,request,signature):
        with self.library.db() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT signature FROM file_upload_attempts WHERE owner=? AND request_id=?',(owner,request)).fetchone()
            if row and row['signature']!=signature:
                raise StaleBasis('This upload attempt has different contents or a different destination. Choose the file and destination again.')
            db.execute('INSERT OR IGNORE INTO file_upload_attempts VALUES (?,?,?,?)',(owner,request,signature,now()))

    def destinations(self,owner,actor,allowed):
        projects=[];conversations=[];unavailable=0
        with self.projects.db() as catalog:
            rows=[dict(p) for p in catalog.execute('SELECT * FROM projects') if p['id'] in allowed]
        for project in rows:
            try:
                info=self.projects.info(project)
                with readonly(project['path']) as db:
                    domains=configured_domains(ReadStore(db))
                    places=[('business','Business Intent')] if actor=='priya' else []
                    places += [(key,d['label']) for key,d in domains.items() if actor in d['authors']]
                    for key,label in places:
                        projects.append(dict(label=info['display_title']+' · '+label,
                            destination=dict(kind='project',project=project['id'],generation=project['version'],domain=key)))
                        if key=='business':continue
                        threads=db.execute("""SELECT r.id,r.revision,r.body FROM records r
                            JOIN (SELECT id,MAX(revision) revision FROM records WHERE kind='domain-conversation' GROUP BY id) t
                            ON r.id=t.id AND r.revision=t.revision WHERE r.scope=? AND json_extract(r.body,'$.owner')=?""",
                            (domains[key]['scope'],actor))
                        for thread in threads:
                            body=json.loads(thread['body'])
                            draft=db.execute("SELECT id,revision,body FROM records WHERE id=? AND kind='contribution-draft' AND scope=? ORDER BY revision DESC LIMIT 1",(body['draft_id'],domains[key]['scope'])).fetchone()
                            if not draft:continue
                            draft_body=json.loads(draft['body'])
                            if draft_body.get('owner')!=actor or not draft_body.get('chassis'):continue
                            conversations.append(dict(label=info['display_title']+' · '+label+' · '+(draft_body.get('title') or 'Domain conversation'),disabled=bool(body.get('pending')),
                                destination=dict(kind='domain-conversation',project=project['id'],generation=project['version'],domain=key,
                                    conversation=dict(id=thread['id'],revision=thread['revision']),expected=dict(id=draft['id'],revision=draft['revision']))))
            except (sqlite3.Error,OSError,ValueError):unavailable+=1
        with self.chat.db() as db:
            for thread in db.execute('SELECT id,title FROM threads WHERE owner=? ORDER BY updated_at DESC',(owner,)):
                if self.chat.blocked(db,thread['id'],allowed):continue
                pending=bool(db.execute("SELECT 1 FROM messages WHERE thread=? AND status='pending'",(thread['id'],)).fetchone())
                conversations.append(dict(label=thread['title'],disabled=pending,destination=dict(kind='conversation',thread=thread['id'])))
        return dict(owner=owner,projects=projects,conversations=conversations,unavailable_locations=unavailable)

    def upload(self,owner,actor,principal,allowed,data):
        if data.get('expected_owner')!=owner:raise StaleBasis('The active user changed. Reopen Upload before saving this file.')
        request=data.get('request_id')
        if not isinstance(request,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',request):raise ValueError('Reopen Upload to start a fresh upload attempt.')
        destination=data.get('destination')
        if not isinstance(destination,dict):raise ValueError('Choose a project or conversation.')
        name=data.get('filename');content=data.get('content')
        if not isinstance(name,str) or not name.strip() or len(name)>250 or not isinstance(content,str):
            raise ValueError('Choose a supported file under 5 MB.')
        try:raw=base64.b64decode(content,validate=True)
        except (ValueError,TypeError):raise ValueError('The file could not be read.') from None
        if not 0<len(raw)<=5*1024*1024:raise ValueError('Choose a supported file under 5 MB.')
        signature=fingerprint(dict(destination=destination,filename=Path(name).name,sha256=hashlib.sha256(raw).hexdigest()))
        self.reserve(owner,request,signature)
        kind=destination.get('kind')
        if kind in {'conversation','new-conversation'}:
            if set(destination)!=({'kind','thread'} if kind=='conversation' else {'kind'}):raise ValueError('Choose a valid conversation destination.')
            result=self.chat.upload_from_files(owner,allowed,data,destination,request,signature)
            answer=dict(id=identifier('chat',result['thread'],result['id']),thread=result['thread'],message='File saved privately to the conversation.')
        elif kind in {'project','domain-conversation'}:
            answer=self._project_upload(owner,actor,principal,allowed,data,destination,request,signature)
        else:raise ValueError('Choose a project or conversation.')
        # Uploading an already archived item explicitly brings its library entry back.
        item=self.library.resolve(owner,actor,allowed,answer['id'])
        if item['archived']:
            self.library.update(owner,actor,allowed,dict(id=answer['id'],action='restore',expected_revision=item['revision']))
        return answer

    def _project_upload(self,owner,actor,principal,allowed,data,destination,request,signature):
        kind=destination['kind'];required={'kind','project','generation','domain'}
        if kind=='domain-conversation':required|={'conversation','expected'}
        if set(destination)!=required or type(destination.get('generation')) is not int:
            raise ValueError('Choose a current project upload location.')
        project_id=destination.get('project');domain=destination.get('domain')
        if project_id not in allowed:raise PermissionError('You are not assigned to this project.')
        with self.projects.locked(project_id,destination['generation']) as project:
            store=Store(project['path'])
            try:
                workspace=Workspace(store,actor,self.model,principal_id=principal,domain_key=domain)
                if domain=='business':
                    if actor!='priya' or kind!='project':raise PermissionError('Use your assigned private project area.')
                elif workspace.domain_key!=domain:raise PermissionError('You are not assigned to this domain.')
                with store.transaction():
                    if kind=='domain-conversation':
                        # Ownership/access first; exact revisions are checked after a retry lookup.
                        workspace.domain_chat.owned(destination['conversation'],current=False)
                    receipt_schema(store.db)
                    result=prior_receipt(store.db,owner,request,signature)
                    if result:return result
                    if kind=='domain-conversation':
                        attached=workspace.domain_chat.attach(dict(conversation=destination['conversation'],expected=destination['expected'],
                            filename=data['filename'],content=data['content']))
                        thread=workspace.domain_chat.owned(attached['conversation'])
                        source=thread['body']['focus_source']
                    elif domain=='business':
                        if not store.db.execute("SELECT 1 FROM records WHERE id='INTAKE-001'").fetchone():
                            workspace.intake.start(dict(title=self.projects.info(project)['title']))
                        source=workspace.coaching.add_source(dict(filename=data['filename'],content=data['content']))['ref']
                    else:source=workspace.domains.import_source(dict(filename=data['filename'],content=data['content']))['ref']
                    result=dict(id=identifier('project',project_id,source['id'],source['revision']),project=project_id,
                        source=source,message='File saved in your private project files.')
                    store.db.execute('INSERT INTO file_upload_requests VALUES (?,?,?,?,?)',(owner,request,signature,json.dumps(result),now()))
                    return result
            finally:store.close()
