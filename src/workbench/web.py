"""Local-only browser adapter. No external requests or model calls."""
import argparse
from dataclasses import asdict, is_dataclass
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import sqlite3
import time
import threading
from urllib.parse import urlsplit, parse_qs, quote
from uuid import uuid4

from .core import Store, StaleBasis
from .decisions import ACTORS, PERSONAS, ADMIN_ACTOR, DecisionBlocked
from .workspace import Workspace
from .domain import configured_domains
from .projects import Projects
from .portfolio import portfolio,project_summary
from .thought_partner import ThoughtPartner
from .my_files import MyFiles
from .file_uploads import FileUploads
from .uploads import upload_owner
from .decision_rights import DecisionRights
from .project_activity import agent_activity
from .access import Access
from .announcements import Announcements
from .enterprise import Enterprise

STATIC = Path(__file__).parent / "static"


def encode(value):
    return json.dumps(value, default=lambda v: asdict(v) if is_dataclass(v) else str(v)).encode()


from .model_provider import load_model, UnconfiguredModel


class BrowserServer(ThreadingHTTPServer):
    daemon_threads = True

    @property
    def workspace_notice(self):
        return self._workspace_notice() if callable(self._workspace_notice) else self._workspace_notice

    @workspace_notice.setter
    def workspace_notice(self, value):
        self._workspace_notice = value

    def __init__(self, address, path, model=None, *, workspace_notice=None, test_profiles=False, development=False, model_connection=None):
        if address[0] != "127.0.0.1":
            raise ValueError("This prototype only listens on 127.0.0.1")
        self._workspace_notice = workspace_notice
        self.model_connection = model_connection
        self.model = model if model is not None else UnconfiguredModel() if model_connection else load_model()
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with_store = Store(self.path)
        with_store.close()
        self.projects = Projects(self.path)
        self.announcements = Announcements(self.projects)
        self.enterprise = Enterprise(self.path, self.projects)
        self.thought_partner = ThoughtPartner(self.path, self.projects, self.model, model_router=model_connection)
        self.my_files = MyFiles(self.path,self.projects,self.thought_partner)
        self.file_uploads = FileUploads(self.projects,self.thought_partner,self.my_files,self.model)
        self.sessions = {}
        self.session_lock = threading.RLock()
        self.development = development
        self.test_profiles = test_profiles or development
        if test_profiles and not development and self.path.with_name(self.path.stem+'-access.sqlite3').exists():
            raise ValueError('This database has account protection. Use an isolated database for test profiles.')
        self.access = None if self.test_profiles else Access(self.path)
        super().__init__(address, Handler)
        if self.access:
            self.access.bootstrap(f"http://127.0.0.1:{self.server_port}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Do not log user-authored content or request credentials.

    def trusted_request(self):
        host = self.headers.get("Host", "")
        expected = f"127.0.0.1:{self.server.server_port}"
        if host != expected:
            return False
        origin = self.headers.get("Origin")
        if origin and origin != f"http://{expected}":
            return False
        return self.headers.get("Sec-Fetch-Site", "") != "cross-site"

    def public_entry_navigation(self):
        # Only the static shell may be entered from a user-activated external link.
        # Never create/read a session or process an API through this exception.
        return (self.command == 'GET' and self.path == '/' and
                self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}' and
                self.headers.get('Origin') is None and
                self.headers.get('Sec-Fetch-Site') == 'cross-site' and
                self.headers.get('Sec-Fetch-Mode') == 'navigate' and
                self.headers.get('Sec-Fetch-Dest') == 'document' and
                self.headers.get('Sec-Fetch-User') == '?1')

    def session(self):
        cookie = SimpleCookie()
        name = f"workbench_session_{self.server.server_port}"
        try:
            cookie.load(self.headers.get("Cookie", ""))
            id = cookie[name].value if name in cookie else None
        except Exception:
            id = None
        with self.server.session_lock:
            now = time.time()
            for key, item in list(self.server.sessions.items()):
                if now-item['seen']>1800 or now-item['created']>28800:
                    self.server.sessions.pop(key, None)
            if id not in self.server.sessions:
                id = secrets.token_urlsafe(32)
                self.server.sessions[id] = {"actor": "priya" if self.server.test_profiles else None,
                    "account": None, "csrf": secrets.token_urlsafe(32), "created": now, "seen": now}
            self.session_id = id
            session = self.server.sessions[id]
            session['seen'] = now
            return session

    def rotate(self, session, account=None):
        with self.server.session_lock:
            self.server.sessions.pop(self.session_id, None)
            self.session_id = secrets.token_urlsafe(32)
            session = {"actor": account['actor'] if account else None,
                       "account": account['id'] if account else None,
                       "csrf": secrets.token_urlsafe(32), "created": time.time(), "seen": time.time()}
            self.server.sessions[self.session_id] = session
            return session

    def principal(self, session):
        return self.server.access.account(session['account']) if session.get('account') else None

    def project_memberships(self, session):
        if self.server.access:
            account=self.principal(session)
            return self.server.access.projects(account) if account else set()
        with self.server.projects.db() as db:
            ids={row[0] for row in db.execute('SELECT id FROM projects')}
            # Imported stores do not silently assign their private sponsor work to
            # a demo contributor. The admin preview can inspect shared-only context.
            if session['actor']!=ADMIN_ACTOR:
                ids-={row[0] for row in db.execute('SELECT target_id FROM project_connections')}
            return ids

    def decision_members(self,project_id):
        if not self.server.access:
            return [dict(actor=a,name=p['name'],role=p['role'],principal=None) for a,p in ACTORS.items()]
        with self.server.access.db() as db:
            return [dict(actor=r['actor'],name=r['username'],role=ACTORS[r['actor']]['role'],principal=r['id'])
                for r in db.execute('SELECT a.id,a.actor,a.username FROM accounts a JOIN memberships m ON m.account=a.id WHERE m.project=?',(project_id,)) if r['actor'] in ACTORS]

    def auth_state(self, session):
        if self.server.test_profiles:
            return dict(mode='development' if self.server.development else 'testing', authenticated=True, administrator=session['actor']==ADMIN_ACTOR, settings_access=bool(self.server.development), csrf=session['csrf'])
        account = self.principal(session)
        return dict(mode='accounts', authenticated=bool(account), csrf=session['csrf'],
                    setup_required=self.server.access.setup_needed(), account=account,
                    projects=sorted(self.server.access.projects(account)) if account else [])

    def send(self, status, body, content_type="application/json; charset=utf-8", *, filename=None):
        payload = body if isinstance(body, bytes) else encode(body)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        if filename:self.send_header("Content-Disposition", "attachment; filename*=UTF-8"+chr(39)*2+quote(filename,safe=""))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        if hasattr(self, "session_id"):
            self.send_header("Set-Cookie", f"workbench_session_{self.server.server_port}={self.session_id}; HttpOnly; SameSite=Strict; Path=/")
        self.end_headers()
        self.wfile.write(payload)

    def enterprise_admin(self, session):
        account = self.principal(session) if self.server.access else None
        return bool(account and account['admin']) or bool(self.server.test_profiles and session['actor'] == ADMIN_ACTOR)

    def can_manage_models(self, session):
        account = self.principal(session) if self.server.access else None
        return bool(account and account['admin']) or bool(self.server.development and session['actor'] in PERSONAS)

    def model_connection_state(self, session, project='__general__'):
        runtime = self.server.model_connection
        if not runtime:
            return None
        admin = self.can_manage_models(session)
        return runtime.state(self.server.projects.listing() if admin else [], admin=admin, project=project)

    def project_model(self, project):
        return self.server.model_connection.select([project]) if self.server.model_connection else self.server.model

    def do_GET(self):
        if self.public_entry_navigation():
            return self.send(200, (STATIC / 'index.html').read_bytes(), 'text/html; charset=utf-8')
        if not self.trusted_request():
            return self.send(403, {"error": "Open this app at its printed 127.0.0.1 address"})
        session = self.session()
        path = urlsplit(self.path).path
        if path == "/api/auth":
            return self.send(200, self.auth_state(session))
        if path.startswith('/api/') and not self.server.test_profiles and not self.principal(session):
            return self.send(401, {"error": "Sign in to open your workspace."})
        if path == '/api/model-connections':
            if not self.server.model_connection or not self.can_manage_models(session):
                return self.send(403, {'error': 'Only the Administrator can manage site-wide model connections.'})
            return self.send(200, self.model_connection_state(session))
        if path == '/api/admin-announcements':
            if not self.can_manage_models(session):
                return self.send(403, {'error': 'Only the Administrator can edit Home announcements.'})
            try:
                return self.send(200, self.server.announcements.state())
            except (sqlite3.Error, OSError):
                return self.send(503, {'error': 'Announcement settings are unavailable. Existing publications have not changed.'})
        if path == '/api/admin-integrations':
            if not self.can_manage_models(session):
                return self.send(403, {'error': 'Only the Administrator can manage project integration settings here.'})
            try:
                listing = self.server.projects.listing()
                project_id = parse_qs(urlsplit(self.path).query).get('project', [None])[0]
                if not project_id:
                    return self.send(200, {'projects': listing})
                with self.server.projects.locked(project_id) as project:
                    store = Store(project['path'])
                    try:
                        # Configuration only: never return the sponsor's intake,
                        # private domain work, user tokens or their authorization.
                        workspace = Workspace(store, session['actor'], UnconfiguredModel(), principal_id=session.get('account'), admin=True)
                        result = {'project': self.server.projects.info(project), 'projects': listing,
                                  'tools': workspace.project_flow.tools(),
                                  'connections': workspace.coaching.settings.connections()}
                    finally:
                        store.close()
                return self.send(200, result)
            except PermissionError as error:
                return self.send(403, {'error': str(error)})
            except (ValueError, sqlite3.Error, OSError):
                return self.send(400, {'error': 'Integration settings are unavailable. Choose an existing project.'})
        if path=='/api/decision-rights':
            account=self.principal(session) if self.server.access else None
            admin=self.can_manage_models(session) or bool(self.server.test_profiles and session['actor']==ADMIN_ACTOR)
            try:
                allowed=self.project_memberships(session)
                listing=self.server.projects.listing() if admin else self.server.projects.listing(allowed_ids=allowed)
                project_id=parse_qs(urlsplit(self.path).query).get('project',[None])[0]
                if not project_id:return self.send(200,dict(projects=listing,can_edit=admin))
                if project_id not in allowed and not admin:raise PermissionError('You are not assigned to this project.')
                with self.server.projects.locked(project_id) as project:
                    store=Store(project['path'])
                    try:result=DecisionRights(store,session['actor'],principal=session.get('account'),admin=admin,members=self.decision_members(project_id)).state()
                    finally:store.close()
                    result['project']=self.server.projects.info(project)
                return self.send(200,result)
            except PermissionError as error:return self.send(403,dict(error=str(error)))
            except (ValueError,sqlite3.Error) as error:return self.send(400,dict(error=str(error)))
        if path in {'/api/home','/api/portfolio','/api/portfolio-access'}:
            account=self.principal(session) if self.server.access else None
            try:
                with self.server.projects.db() as catalog:all_ids={p[0] for p in catalog.execute('SELECT id FROM projects')}
                memberships=self.project_memberships(session)
                visible=self.server.access.portfolio_projects(account) if account else all_ids if self.server.development and session['actor']==ADMIN_ACTOR else set()
                if path=='/api/portfolio-access':
                    if account and account['admin']:return self.send(200,self.server.access.portfolio_configuration(account,self.server.projects.listing()))
                    if self.server.development:return self.send(200,dict(preview=True,accounts=[],projects=self.server.projects.listing()))
                    raise PermissionError('Only an administrator can manage portfolio visibility.')
                if path=='/api/portfolio':
                    if not visible:raise PermissionError('Project oversight visibility has not been assigned.')
                    return self.send(200,dict(projects=portfolio(self.server.projects,visible | memberships,memberships),preview=bool(self.server.development)))
                mine=self.server.projects.listing(actor=session['actor'],allowed_ids=memberships)
                if session['actor']!='priya':
                    mine=[project_summary(self.server.projects,self.server.projects.current(p['id']),True) for p in mine]
                return self.send(200,dict(global_context=True,actor=session['actor'],actors=PERSONAS,auth=self.auth_state(session),csrf=session['csrf'],initialized=False,
                    project=dict(id=None,version=0,title=''),records=[],requirement_impacts={},saved_versions=[],intake={},domains=dict(active=None,profiles=[],can_configure=[]),
                    domain_knowledge=dict(domains=[],can_add=False),projects=mine,overview=portfolio(self.server.projects,visible | memberships,memberships) if visible else None,
                    portfolio=dict(available=bool(visible & all_ids),preview=bool(self.server.development)),workspace_notice=self.server.workspace_notice,model_connection=self.model_connection_state(session),announcements=self.server.announcements.public()))
            except PermissionError as error:return self.send(403,{'error':str(error)})
            except (sqlite3.Error,OSError,ValueError):return self.send(503,{'error':'Project overview is unavailable. Existing work has not been changed.'})
        if path in {'/api/my-files','/api/my-file','/api/my-file-download','/api/my-file-destinations'}:
            account=self.principal(session) if self.server.access else None
            owner=upload_owner(session['actor'],account['id'] if account else None)
            allowed=self.project_memberships(session);query=parse_qs(urlsplit(self.path).query)
            try:
                if path=='/api/my-file-destinations':return self.send(200,self.server.file_uploads.destinations(owner,session['actor'],allowed))
                if path=='/api/my-files':return self.send(200,self.server.my_files.listing(owner,session['actor'],allowed))
                file_id=query.get('id',[''])[0]
                if path=='/api/my-file':return self.send(200,self.server.my_files.detail(owner,session['actor'],allowed,file_id))
                content,name,mime=self.server.my_files.download(owner,session['actor'],allowed,file_id,query.get('format',['original'])[0])
                return self.send(200,content,mime,filename=name)
            except PermissionError:return self.send(403,{'error':'This file is not available in your library.'})
            except StaleBasis as error:return self.send(409,{'error':str(error)})
            except ValueError as error:return self.send(400,{'error':str(error)})
            except (sqlite3.Error,OSError):return self.send(503,{'error':'Your file library is unavailable. Existing files have not been changed.'})
        if path in {"/api/thought-chat","/api/thought-chat-document","/api/thought-chat-download"}:
            account=self.principal(session) if self.server.access else None
            owner='account:'+account['id'] if account else 'profile:'+session['actor']
            allowed=self.project_memberships(session)
            query=parse_qs(urlsplit(self.path).query)
            try:
                if path.endswith('-download'):return self.send(200,self.server.thought_partner.download_document(owner,allowed,query.get('thread',[None])[0],query.get('document',[None])[0]),'application/octet-stream')
                if path.endswith('-document'):return self.send(200,self.server.thought_partner.document(owner,allowed,query.get('thread',[None])[0],query.get('document',[None])[0]))
                return self.send(200,self.server.thought_partner.state(owner,allowed,query.get('thread',[None])[0],query.get('q',[''])[0]))
            except PermissionError as error:return self.send(403,{'error':str(error)})
            except (ValueError,KeyError,TypeError):return self.send(400,{'error':'This conversation could not be opened.'})
            except (sqlite3.Error,OSError):return self.send(503,{'error':'Conversation storage is unavailable. Your existing conversations are retained.'})
        if path == "/api/project-agent-activity":
            query = parse_qs(urlsplit(self.path).query)
            project_id = query.get("project", [""])[0]
            version = query.get("generation", [""])[0]
            try:
                if not project_id or not version:
                    raise ValueError("Open a project before viewing its activity.")
                account = self.principal(session) if self.server.access else None
                if project_id not in self.project_memberships(session):
                    raise PermissionError("You do not have access to this project.")
                project = self.server.projects.current(project_id, version)
                result = agent_activity(project["path"])
                # A reset during the read must not return activity from a retired generation.
                self.server.projects.current(project_id, version)
                return self.send(200, result)
            except PermissionError as error:
                return self.send(403, {"error": str(error)})
            except StaleBasis:
                return self.send(409, {"error": "Project changed. Reload to see its activity."})
            except ValueError as error:
                return self.send(400, {"error": str(error)})
            except sqlite3.Error:
                return self.send(503, {"error": "Could not read agent activity. Try again."})
        if path == "/api/design-page":
            from .visual_pdf import page as pdf_page
            query=parse_qs(urlsplit(self.path).query)
            try:
                project_id=query.get('project',[''])[0]
                account=self.principal(session) if self.server.access else None
                if project_id not in self.project_memberships(session):raise PermissionError('Page unavailable in this project')
                with self.server.projects.locked(project_id,query.get('generation',[''])[0]) as project:
                    store=Store(project['path'])
                    try:
                        _,image=pdf_page(Workspace(store,session['actor'],self.project_model(project_id)),dict(id=query.get('source',[''])[0],revision=int(query.get('revision',['0'])[0])),int(query.get('page',['0'])[0]))
                    finally:store.close()
                return self.send(200,image,'image/png')
            except PermissionError:return self.send(403,{'error':'Page unavailable in this context'})
            except (ValueError,KeyError,TypeError) as error:return self.send(400,{'error':str(error)})
            except (sqlite3.Error,OSError):return self.send(503,{'error':'Could not open the retained PDF page'})
        if path == '/api/enterprise':
            try:
                return self.send(200, self.server.enterprise.state(session['actor'], self.enterprise_admin(session), self.project_memberships(session)))
            except (sqlite3.Error, OSError):
                return self.send(503, {'error': 'Enterprise context is unavailable. Nothing has changed.'})
        if path == "/api/state":
            project_id = parse_qs(urlsplit(self.path).query).get("project", ["original"])[0]
            try:
                account = self.principal(session) if self.server.access else None
                if project_id not in self.project_memberships(session):
                    raise PermissionError('You do not have access to this project.')
                with self.server.projects.locked(project_id) as project:
                    store = Store(project["path"])
                    try:
                        result = Workspace(store, session["actor"], self.project_model(project_id), principal_id=session.get("account"), admin=bool(account and account["admin"]) or bool(self.server.test_profiles and session['actor']==ADMIN_ACTOR), domain_key=session.get("domains",{}).get(project_id), decision_members=self.decision_members(project_id), settings_access=self.server.development).state()
                    finally:
                        store.close()
                    listing = self.server.projects.listing(actor=session["actor"], allowed_ids=self.project_memberships(session))
                    if account:
                        allowed = self.server.access.projects(account)
                        listing = [p for p in listing if p['id'] in allowed]
                        result['domains']['profiles'] = [p for p in result['domains']['profiles']
                            if account['admin'] or p['key']==result['domains']['active']]
                    result['enterprise'] = self.server.enterprise.state(session['actor'], self.enterprise_admin(session), self.project_memberships(session))
                    result.update(portfolio=dict(available=bool(self.server.access.portfolio_projects(account)) if account else bool(self.server.development and session['actor']==ADMIN_ACTOR),preview=bool(self.server.development)),auth=self.auth_state(session), csrf=session["csrf"], database=project["path"],
                                  workspace_notice=self.server.workspace_notice,model_connection=self.model_connection_state(session,project_id),
                                  project=self.server.projects.info(project),
                                  projects=listing,
                                  saved_versions=self.server.projects.history(project_id) if session["actor"]=="priya" else [])
                return self.send(200, result)
            except PermissionError as error:
                return self.send(403, {"error": str(error)})
            except ValueError as error:
                return self.send(400, {"error": str(error)})
            except sqlite3.Error:
                return self.send(503, {"error": "Could not open the saved project. Its data has not been reset."})
        files = {"/integrity-gaps.js": ("integrity-gaps.js", "text/javascript; charset=utf-8"), "/integrity-gaps.css": ("integrity-gaps.css", "text/css; charset=utf-8"), "/knowledge-cards.js": ("knowledge-cards.js", "text/javascript; charset=utf-8"), "/knowledge-dossier.js": ("knowledge-dossier.js", "text/javascript; charset=utf-8"), "/context.js": ("context.js", "text/javascript; charset=utf-8"), "/developer-brief.js": ("developer-brief.js", "text/javascript; charset=utf-8"), "/domain-prototypes.js": ("domain-prototypes.js", "text/javascript; charset=utf-8"), "/domain-flows.js": ("domain-flows.js", "text/javascript; charset=utf-8"), "/domain-development.js": ("domain-development.js", "text/javascript; charset=utf-8"), "/decision-rights.js": ("decision-rights.js", "text/javascript; charset=utf-8"), "/file-upload.js": ("file-upload.js", "text/javascript; charset=utf-8"), "/my-files.js": ("my-files.js", "text/javascript; charset=utf-8"), "/thought-partner.js": ("thought-partner.js", "text/javascript; charset=utf-8"), "/working-report.js": ("working-report.js", "text/javascript; charset=utf-8"), "/domain-knowledge.js": ("domain-knowledge.js", "text/javascript; charset=utf-8"), "/domain-interpretation.js": ("domain-interpretation.js", "text/javascript; charset=utf-8"), "/project-flow.js": ("project-flow.js", "text/javascript; charset=utf-8"), "/domain-chat.js": ("domain-chat.js", "text/javascript; charset=utf-8"), "/domain-chat.css": ("domain-chat.css", "text/css; charset=utf-8"), "/design-visual.js": ("design-visual.js", "text/javascript; charset=utf-8"), "/design-visual.css": ("design-visual.css", "text/css; charset=utf-8"), "/home.js": ("home.js", "text/javascript; charset=utf-8"), "/home.css": ("home.css", "text/css; charset=utf-8"), "/home-file-text.svg": ("home-file-text.svg", "image/svg+xml"), "/home-plus.svg": ("home-plus.svg", "image/svg+xml"), "/home-circle-help.svg": ("home-circle-help.svg", "image/svg+xml"), "/home-clock.svg": ("home-clock.svg", "image/svg+xml"), "/home-shield.svg": ("home-shield.svg", "image/svg+xml"), "/home-target.svg": ("home-target.svg", "image/svg+xml"), "/home-chart-no-axes-column-increasing.svg": ("home-chart-no-axes-column-increasing.svg", "image/svg+xml"), "/home-book-open.svg": ("home-book-open.svg", "image/svg+xml"), "/home-check.svg": ("home-check.svg", "image/svg+xml"), "/home-arrow-right.svg": ("home-arrow-right.svg", "image/svg+xml"), "/workspace.css": ("workspace.css", "text/css; charset=utf-8"), "/theme.css": ("theme.css", "text/css; charset=utf-8"), "/theme.js": ("theme.js", "text/javascript; charset=utf-8"), "/case.js": ("case.js", "text/javascript; charset=utf-8"), "/cockpit.js": ("cockpit.js", "text/javascript; charset=utf-8"), "/meaning.js": ("meaning.js", "text/javascript; charset=utf-8"), "/enterprise.js": ("enterprise.js", "text/javascript; charset=utf-8"), "/space-grotesk-latin-500.woff2": ("space-grotesk-latin-500.woff2", "font/woff2"), "/space-grotesk-latin-600.woff2": ("space-grotesk-latin-600.woff2", "font/woff2"), "/inter-latin.woff2": ("inter-latin.woff2", "font/woff2"), "/sponsor.js": ("sponsor.js", "text/javascript; charset=utf-8"), "/delivery.js": ("delivery.js", "text/javascript; charset=utf-8"), "/demo-delivery.js": ("demo-delivery.js", "text/javascript; charset=utf-8"), "/sponsor.css": ("sponsor.css", "text/css; charset=utf-8"), "/bridge.js": ("bridge.js", "text/javascript; charset=utf-8"), "/preflight.js": ("preflight.js", "text/javascript; charset=utf-8"), "/field-coach.js": ("field-coach.js", "text/javascript; charset=utf-8"), "/access.js": ("access.js", "text/javascript; charset=utf-8"), "/packets.js": ("packets.js", "text/javascript; charset=utf-8"), "/domains.js": ("domains.js", "text/javascript; charset=utf-8"), "/goals.js": ("goals.js", "text/javascript; charset=utf-8"), "/scaffold-tailoring.js": ("scaffold-tailoring.js", "text/javascript; charset=utf-8"), "/scaffold.js": ("scaffold.js", "text/javascript; charset=utf-8"), "/document-changes.js": ("document-changes.js", "text/javascript; charset=utf-8"), "/agent-quality.js": ("agent-quality.js", "text/javascript; charset=utf-8"), "/requirement-agent.js": ("requirement-agent.js", "text/javascript; charset=utf-8"), "/settings.js": ("settings.js", "text/javascript; charset=utf-8"), "/projects.js": ("projects.js", "text/javascript; charset=utf-8"), "/value.js": ("value.js", "text/javascript; charset=utf-8"),"/coaching.js": ("coaching.js", "text/javascript; charset=utf-8"), "/refinements.js": ("refinements.js", "text/javascript; charset=utf-8"), "/": ("index.html", "text/html; charset=utf-8"), "/app.js": ("app.js", "text/javascript; charset=utf-8"), "/resolution.js": ("resolution.js", "text/javascript; charset=utf-8"), "/intake.js": ("intake.js", "text/javascript; charset=utf-8"), "/style.css": ("style.css", "text/css; charset=utf-8")}
        files["/team-timeline.js"] = ("team-timeline.js", "text/javascript; charset=utf-8")
        files["/team-timeline-links.js"] = ("team-timeline-links.js", "text/javascript; charset=utf-8")
        files["/signals.js"] = ("signals.js", "text/javascript; charset=utf-8")
        files["/reviewer-ui.js"] = ("reviewer-ui.js", "text/javascript; charset=utf-8")
        files["/reviewer-ui.css"] = ("reviewer-ui.css", "text/css; charset=utf-8")
        files["/alignment.css"] = ("alignment.css", "text/css; charset=utf-8")
        files["/signals.css"] = ("signals.css", "text/css; charset=utf-8")
        files["/signal-accountability.css"] = ("signal-accountability.css", "text/css; charset=utf-8")
        files["/requirement-assessments.js"] = ("requirement-assessments.js", "text/javascript; charset=utf-8")
        files["/requirement-evidence.js"] = ("requirement-evidence.js", "text/javascript; charset=utf-8")
        files["/requirement-assessments.css"] = ("requirement-assessments.css", "text/css; charset=utf-8")
        files["/requirement-organization.js"] = ("requirement-organization.js", "text/javascript; charset=utf-8")
        files["/requirement-organization.css"] = ("requirement-organization.css", "text/css; charset=utf-8")
        files["/business-assessments.js"] = ("business-assessments.js", "text/javascript; charset=utf-8")
        files["/business-assessments.css"] = ("business-assessments.css", "text/css; charset=utf-8")
        if path not in files:
            return self.send(404, {"error": "Not found"})
        file, content_type = files[path]
        self.send(200, (STATIC / file).read_bytes(), content_type)

    def do_POST(self):
        if not self.trusted_request():
            return self.send(403, {"error": "Cross-origin requests are not allowed"})
        session = self.session()
        if not secrets.compare_digest(self.headers.get("X-CSRF-Token", ""), session["csrf"]):
            return self.send(403, {"error": "Session changed. Reload the page before saving"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "JSON required"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= (8 * 1024 * 1024 if urlsplit(self.path).path in {"/api/intake-source", "/api/domain-source", "/api/design-pdf-attach", "/api/domain-chat-attach", "/api/domain-submission-import", "/api/thought-chat-attach", "/api/my-file-upload"} else 262144):
                return self.send(413, {"error": "Request too large or empty"})
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError("Expected an object")
        except (ValueError, json.JSONDecodeError):
            return self.send(400, {"error": "Invalid request"})
        action = urlsplit(self.path).path.removeprefix("/api/")
        if action in {'auth-login','auth-enroll','auth-logout'}:
            if self.server.test_profiles:
                return self.send(400, {'error':'Accounts are disabled in this explicit test server.'})
            try:
                if action=='auth-logout':
                    session=self.rotate(session)
                else:
                    if action=='auth-enroll':
                        account=self.server.access.enroll(data.get('token',''), data.get('username',''), data.get('password'),
                            [p['id'] for p in self.server.projects.listing()])
                    else:
                        account=self.server.access.login(data.get('username',''),data.get('password'))
                    session=self.rotate(session,account)
                return self.send(200,self.auth_state(session))
            except (ValueError,PermissionError) as error:
                return self.send(400 if isinstance(error,ValueError) else 401,{'error':str(error)})
            except (sqlite3.Error,OSError):
                return self.send(503,{'error':'Account storage is unavailable. Please try again.'})
        account=self.principal(session) if self.server.access else None
        if self.server.access and not account:
            return self.send(401, {'error':'Sign in to continue.'})
        if action == "profile":
            if not self.server.test_profiles:
                return self.send(403, {'error':'Your account determines your domain and permissions. Sign out to use another account.'})
            if data.get("actor") not in PERSONAS:
                return self.send(400, {"error": "Unknown profile"})
            session["actor"] = data["actor"]
            session.pop('domains',None)
            return self.send(200, {"message": "Local profile switched"})
        try:
            if action in {'announcements-save', 'announcements-publish'}:
                if not self.can_manage_models(session):
                    raise PermissionError('Only the Administrator can edit or publish Home announcements.')
                author = {'id': 'account:'+account['id'] if account else 'profile:'+session['actor'],
                          'name': account['username'] if account else PERSONAS[session['actor']]['name']}
                operation = self.server.announcements.save if action == 'announcements-save' else self.server.announcements.publish
                return self.send(200, operation(data, author))
            if action in {'admin-integration-save', 'admin-work-tools-save'}:
                if not self.can_manage_models(session):
                    raise PermissionError('Only the Administrator can manage project integration settings here.')
                project_id = self.headers.get('X-Workbench-Project')
                version = self.headers.get('X-Workbench-Version')
                if not project_id or not version:
                    raise StaleBasis('Choose a project before saving integration settings.')
                with self.server.projects.locked(project_id, version) as project:
                    store = Store(project['path'])
                    try:
                        workspace = Workspace(store, session['actor'], UnconfiguredModel(), principal_id=session.get('account'), admin=True)
                        result = workspace.project_flow.save_tools(data) if action == 'admin-work-tools-save' else workspace.coaching.settings.save_connection(data, admin=True, principal=session.get('account'))
                    finally:
                        store.close()
                return self.send(200, result)
            if action in {'model-connection-save', 'model-connection-test', 'model-connection-assign', 'model-connection-remove'}:
                if not self.server.model_connection or not self.can_manage_models(session):
                    raise PermissionError('Only the Administrator can manage site-wide model connections.')
                runtime = self.server.model_connection
                author = 'account:' + account['id'] if account else 'profile:' + session['actor']
                if action == 'model-connection-assign':
                    return self.send(200, runtime.assign(data, author, {p['id'] for p in self.server.projects.listing()}))
                operation = {'model-connection-save': runtime.save, 'model-connection-test': runtime.test,
                             'model-connection-remove': runtime.remove}[action]
                return self.send(200, operation(data, author))
            if action=='portfolio-access-save':
                if not account or not account['admin']:raise PermissionError('Only an administrator can manage portfolio visibility.')
                with self.server.projects.db() as catalog:valid={p[0] for p in catalog.execute('SELECT id FROM projects')}
                return self.send(200,self.server.access.save_portfolio_visibility(account,data,valid))
            if action=='my-file-upload':
                owner=upload_owner(session['actor'],account['id'] if account else None)
                return self.send(200,self.server.file_uploads.upload(owner,session['actor'],account['id'] if account else None,self.project_memberships(session),data))
            if action=='my-file-update':
                owner=upload_owner(session['actor'],account['id'] if account else None)
                return self.send(200,self.server.my_files.update(owner,session['actor'],self.project_memberships(session),data))
            if action in {'thought-chat-create','thought-chat-send','thought-chat-attach','thought-chat-document-update'}:
                owner='account:'+account['id'] if account else 'profile:'+session['actor']
                allowed=self.project_memberships(session)
                chat=self.server.thought_partner
                result=chat.create(owner,data) if action=='thought-chat-create' else chat.attach(owner,allowed,data) if action=='thought-chat-attach' else chat.update_document(owner,allowed,data) if action=='thought-chat-document-update' else chat.send(owner,allowed,data)
                return self.send(200,result)
            if action in {'enterprise-session-create', 'enterprise-session-save', 'enterprise-session-close'}:
                enterprise = self.server.enterprise
                if action == 'enterprise-session-create':
                    return self.send(200, enterprise.create_session(session['actor'], self.project_memberships(session), data))
                return self.send(200, (enterprise.save_session if action == 'enterprise-session-save' else enterprise.close_session)(session['actor'], data))
            if action in {'enterprise-roles-save', 'enterprise-propose', 'enterprise-decide', 'enterprise-close'}:
                enterprise = self.server.enterprise
                actor = session['actor']
                if action == 'enterprise-roles-save':
                    return self.send(200, enterprise.save_roles(actor, self.enterprise_admin(session), data))
                if action == 'enterprise-propose':
                    return self.send(200, enterprise.propose(actor, self.project_memberships(session), data))
                if action == 'enterprise-decide':
                    return self.send(200, enterprise.decide(actor, self.project_memberships(session), data))
                return self.send(200, enterprise.close(actor, data))
            if action == "project-create":
                result=self.server.projects.create(data, session["actor"])
                if account:self.server.access.grant(account['id'],result['project_id'],account['id'])
                return self.send(200,result)
            project_id = self.headers.get("X-Workbench-Project")
            version = self.headers.get("X-Workbench-Version")
            if not project_id or not version:
                raise StaleBasis("Reload this page before saving so the destination project can be verified.")
            if project_id not in self.project_memberships(session) and not ((account and account['admin'] and action in {'access-members','access-invite','access-revoke','decision-rights-save'}) or (self.server.development and action=='decision-rights-save')):
                raise PermissionError('You do not have access to this project.')
            with self.server.projects.locked(project_id, version) as project:
                if action in {'access-members','access-invite','access-revoke'}:
                    if not account:raise PermissionError('Account administration requires authenticated mode.')
                    if action=='access-members':result=self.server.access.members(account,project_id)
                    elif action=='access-invite':result=self.server.access.invite(account,project_id,data.get('actor'))
                    else:result=self.server.access.revoke(account,project_id,data.get('account'))
                    return self.send(200,result)
                if action=='domain-select':
                    store=Store(project['path'])
                    try:
                        chosen=data.get('domain');profiles=configured_domains(store)
                        if chosen!='project' and (chosen not in profiles or session['actor'] not in profiles[chosen]['authors']):raise PermissionError('You are not assigned to this domain')
                        session.setdefault('domains',{})[project_id]=chosen
                    finally:store.close()
                    return self.send(200,{'message':'Domain workspace selected.'})
                if action in {"project-reset", "project-restore"}:
                    result = self.server.projects.replace(project, data, session["actor"], action == "project-restore")
                else:
                    store = Store(project["path"])
                    try:
                        workspace=Workspace(store, session["actor"], self.project_model(project_id), principal_id=session.get("account"), admin=bool(account and account["admin"]) or bool(self.server.test_profiles and session['actor']==ADMIN_ACTOR), domain_key=session.get("domains",{}).get(project_id), decision_members=self.decision_members(project_id), settings_access=self.server.development)
                        if action in {'domain-add','domain-update'} and account and account['admin']:
                            member_actors={m['actor'] for m in self.server.access.members(account,project_id)['members']}
                            if not set(data.get('members',[]))<=member_actors:raise ValueError('Add the user to this project before assigning domain access')
                        displayed=self.headers.get('X-Workbench-Domain')
                        if displayed is not None and displayed!=(workspace.domains.key or 'project'):raise StaleBasis('The active domain changed in another tab. Reload before saving.')
                        if isinstance(data, dict):
                            data.pop('_enterprise', None); data.pop('_project', None)
                            if action == 'enterprise-adopt':
                                data['_enterprise'] = self.server.enterprise.current_concept(data.get('concept'))
                                data['_project'] = project_id
                        result = workspace.command(action, data)
                    finally:
                        store.close()
                self.send(200, result if isinstance(result, dict) else {"message": result})
        except PermissionError as error:
            self.send(403, {"error": str(error)})
        except (StaleBasis, DecisionBlocked) as error:
            self.send(409, {"error": str(error)})
        except (ValueError, KeyError, TypeError) as error:
            self.send(400, {"error": str(error)})
        except (sqlite3.Error, OSError):
            self.send(503, {"error": "Could not save. Your existing project is retained; try again."})



def main():
    parser = argparse.ArgumentParser(description="Start the local Intelligence Workbench browser app")
    parser.add_argument("--db", type=Path, help="Use an existing database, including the terminal walkthrough")
    parser.add_argument("--new", action="store_true", help="Create a separate empty workspace")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--coach-env", type=Path, help="One-time import from an existing server-only model configuration")
    parser.add_argument("--model-settings", type=Path, help="Admin-managed local model connections and project assignments")
    parser.add_argument("--import-server-model", action="store_true", help="Explicitly retain the existing local model for current projects on first setup")
    parser.add_argument("--test-profiles", action="store_true", help="Explicit isolated testing only: allow role switching without accounts")
    parser.add_argument("--development", action="store_true", help="Local development: skip sign-in on the existing workspace and allow role switching; retain account records")
    args = parser.parse_args()
    if args.db and args.new:
        parser.error("Choose --db or --new")
    path = args.db or Path("data") / (f"browser-{uuid4().hex[:8]}.sqlite3" if args.new else "workbench.sqlite3")
    try:
        from .model_connection import ModelConnections
        settings_path=args.model_settings or path.with_name(path.stem+'-model-connections.json')
        runtime=ModelConnections(settings_path)
        if (args.import_server_model or args.coach_env) and not settings_path.exists():
            runtime.import_existing(load_model(args.coach_env), {p['id'] for p in Projects(path).listing()})
        server = BrowserServer(("127.0.0.1", args.port), path, test_profiles=args.test_profiles, development=args.development, model_connection=runtime)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Could not start: {error}. Try --port 8766 if the port is in use.\n")
    print(f"\nIntelligence Workbench: http://127.0.0.1:{server.server_port}", flush=True)
    print(f"Database: {path.resolve()}", flush=True)
    if server.development:
        print("LOCAL DEVELOPMENT: no sign-in; role switching enabled. Existing accounts are retained.", flush=True)
    elif server.test_profiles:
        print("TEST MODE: switchable local roles, no authenticated isolation.", flush=True)
    elif server.access.setup_needed():
        print(f"Create your administrator account using the private link in {server.access.setup_file}", flush=True)
    else:
        print("Local account sign-in required. Enterprise SSO is not connected.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped. Your work is saved.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
