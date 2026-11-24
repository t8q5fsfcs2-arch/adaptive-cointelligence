"""Read-only portfolio projection: explicit visibility and shared records only.

Portfolio visibility is not project membership, administrative authority or private
work access. No source text, chat store, private document, draft or agent-run store
is read by this projection.
"""
from pathlib import Path
import json
import sqlite3
from .decisions import SCOPE,ACTORS

KINDS=('project','intent','requirement','contribution','bridge-issue','decision-case','intake-case','project-work-request','intent-decision','decision')
CLOSED={'approved','rejected','published','resolved','cancelled','canceled','withdrawn','completed'}


def person(value):
    return ACTORS.get(value,{}).get('name',str(value or 'Not recorded')) if isinstance(value,str) else 'Not recorded'


def project_summary(catalog,project,can_open):
    meta=catalog.info(project)
    with sqlite3.connect(Path(project['path']).as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('SELECT r.id,r.revision,r.kind,r.body FROM records r JOIN (SELECT id,MAX(revision) revision FROM records GROUP BY id) v ON r.id=v.id AND r.revision=v.revision WHERE r.scope=? AND r.kind IN ('+','.join('?' for _ in KINDS)+')',(SCOPE,*KINDS)).fetchall()
    records=[dict(id=i,revision=v,kind=k,body=json.loads(b)) for i,v,k,b in rows]
    records=[r for r in records if not (r['kind'] in {'contribution','decision-case','intake-case'} and r['body'].get('status') in {'draft','working','private','unpublished'})]
    of=lambda kind:[r for r in records if r['kind']==kind]
    issues=[r for r in of('bridge-issue') if r['body'].get('status') not in CLOSED]
    decisions=[r for r in records if r['kind'] in {'decision-case','intake-case'} and r['body'].get('status') not in CLOSED]
    work=[r for r in of('project-work-request') if r['body'].get('status') not in CLOSED]
    teams=set()
    for r in of('contribution'):
        team=r['body'].get('domain_key') or r['body'].get('domain')
        if isinstance(team,str) and team:teams.add(team.replace('-',' ').title())
    for r in work:
        if isinstance(r['body'].get('recipient_domain'),str):teams.add(r['body']['recipient_domain'].replace('-',' ').title())
    contributions=sorted(of('contribution'),key=lambda r:r['body'].get('published_at') or '',reverse=True)
    latest=(str(contributions[0]['body'].get('domain_key') or contributions[0]['body'].get('domain') or 'Domain').replace('-',' ').title()+' work shared') if contributions else 'Business Intent shared' if of('intent') else 'Requirements shared' if of('requirement') else 'No shared work yet'
    at=max([r['body'][key] for r in records for key in ('published_at','updated_at','at','requested_at') if isinstance(r['body'].get(key),str)],default=None)
    sponsor=next((r['body'].get('sponsor') for r in of('project') if r['body'].get('sponsor')),None)
    return dict(**meta,can_open=can_open,sponsor=person(sponsor),teams=sorted(teams),latest_shared=latest,last_shared_activity=at,
                brief_status='published' if of('intent') else 'unshared',brief_revision=of('intent')[0]['revision'] if of('intent') else None,
                open_issues=len(issues),pending_decisions=len(decisions),open_assignments=len(work),
                attention=[dict(title=str(r['body'].get('title') or 'Project question')[:200],status=str(r['body'].get('status') or 'open')[:80],next_owner=person(r['body'].get('next_owner') or r['body'].get('owner'))) for r in issues[:5]],
                assignments=[dict(title=str(r['body'].get('title') or 'Working brief')[:200],status=str(r['body'].get('status') or 'requested')[:80],owner=person(r['body'].get('recipient'))) for r in work[:5]])


def portfolio(catalog,visible,memberships):
    if not visible:raise PermissionError('Portfolio visibility has not been assigned to this account.')
    with catalog.db() as db:projects=[dict(r) for r in db.execute('SELECT * FROM projects ORDER BY created_at,id') if r['id'] in visible]
    return [project_summary(catalog,p,p['id'] in memberships) for p in projects]
