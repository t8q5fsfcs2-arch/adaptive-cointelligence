"""Portable, isolated Riverbend Health walkthrough. Scripted fixtures; real workflow services."""
import argparse
import base64
from contextlib import closing
from dataclasses import asdict
import http.client
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading

from .core import Store
from .decisions import SCOPE
from .domain_brief import BRIEF_ESSENTIALS
from .domain_knowledge import snapshot
from .model_provider import UnconfiguredModel
from .clinic_demo import populate as seed_decision, NOTICE, BOUNDARY, FIGJAM_FLOW
from .validation import reference
from .workspace import Workspace

MARKER = 'DEMO-PORTABLE-RIVERBEND-v1'
NOTICE_TEXT = 'Synthetic Riverbend Health demo · Connect AI in Settings → Model connections · Figma and Jira/ADO steps need your own connections'


class PrototypeFixture:
    """Used only to seed a labelled example, never as the browser's model adapter."""
    def status(self):
        return dict(configured=True, provider='SCRIPTED DEMO FIXTURE', model='riverbend-package-v1')

    def generate(self, *, instructions, context, schema):
        if 'working_design_brief' not in context:
            raise AssertionError('The package fixture only prepares prototype alternatives.')
        reqs = [r['ref']['id'] for r in context['requirements']]
        section = context['working_design_brief']['adopted'][0]['id']
        concepts = [
            ('A', 'Reminder bot with confirm and cancel', 'A reminder with one-tap confirm or cancel may release slots earlier than today.',
             [('capture', 'Your appointment is Thursday 9:30', 'Synthetic reminder with confirm and cancel replies.', 'Booked', 'Reply', 'Reply C to confirm or X to cancel'),
              ('recovery', 'Cancel this appointment?', 'Cancel releases the slot; rescheduling still needs a call.', 'Not changed yet', 'Reason (optional)', 'Work schedule'),
              ('confirmed', 'Cancelled. Call to rebook.', 'Shown only after the scheduling system stores the change.', 'Cancelled', 'Clinic phone', '555-0142, 8am to 5pm')]),
            ('B', 'Conversational rescheduling agent', 'An AI agent that offers open slots in the conversation may let patients reschedule without calling.',
             [('capture', 'Need to change Thursday 9:30?', 'Synthetic chat; the agent offers only slots the scheduling system reports as open.', 'Booked', 'Your message', 'Can I move it to next week?'),
              ('recovery', 'This visit needs our staff', 'Restricted visit type: handoff with reason and preferred times retained.', 'Sent to staff', 'Preferred times', 'Weekday mornings'),
              ('confirmed', 'Moved to Tue 2:15', 'Confirmation appears only after the change is stored.', 'Rescheduled', 'New time', 'Tuesday 2:15pm, Eastside Clinic')]),
            ('C', 'Self-serve page with AI waitlist', 'A reschedule link plus an AI waitlist may refill released time.',
             [('capture', 'Pick a new time', 'Synthetic self-serve page reached from the reminder link.', 'Booked', 'Open slots', 'Mon 10:00 · Tue 2:15 · Wed 4:30'),
              ('recovery', 'That time was just taken', 'The page refreshes open slots; the original appointment is kept.', 'Not changed', 'Next open slot', 'Wednesday 4:30pm'),
              ('confirmed', 'Moved. Your old slot went to the waitlist.', 'Stored change; released slot offered to the waitlist.', 'Rescheduled', 'Waitlist', 'Slot offered to 3 waiting patients')])]
        variants = []
        for key, name, hypothesis, rows in concepts:
            screens = [dict(key=state, title=title, description=description, status=status,
                            fields=[dict(label=label, value=value, help='Synthetic content; no patient data.')],
                            actions=[dict(label='Continue', destination=dict(capture='recovery', recovery='confirmed', confirmed='capture')[state])],
                            requirement_ids=reqs, brief_section_ids=[section])
                       for state, title, description, status, label, value in rows]
            variants.append(dict(key=key, name=name, hypothesis=hypothesis,
                                 change=name+'; keep the patient task, visit-type rules and stored-only confirmation constant.', screens=screens))
        plan=dict(title='Riverbend appointment assistant: three synthetic concepts',
            hypothesis='Making it easy to change an appointment early may release and refill slots; human testing is still required.',
            variants=variants, factors=[dict(name='Change interaction', levels=['Reply-based cancel','Conversational agent','Self-serve page with waitlist'], why='Compare the same rescheduling task across interaction models.')],
            test_plan={k:'A human researcher must establish the method and actual evidence. No winner or test outcome is claimed.' for k in ('question','task','success_signals','controls','allocation','evidence_needed','decision_rule','limitations')},
            open_questions=['No real patient testing, scheduling-system integration, runtime telemetry or financial outcome is supplied.'])
        return dict(output=plan, model='riverbend-package-v1')


def brief(lee):
    lee.command('domain-brief-create', {})
    row=lee.domain_brief.state()[0]
    texts={
        'purpose':'Help patients change appointments early without a phone call, so released time can be refilled.',
        'scope':'Reminders, cancel, reschedule, staff handoff for restricted visit types and waitlist refill. Exclude clinical advice, triage and emergencies.',
        'users-and-tasks':'Patients change appointments between work and family commitments; front-desk staff handle restricted visit types and the waitlist.',
        'validation':'Compare concepts with actual patients, including accessibility checks. Test stored-only confirmation and slot availability separately.',
        'deliverable':'Three comparable concepts in Figma, a researcher-editable test plan, and a developer brief clearly marking remaining evidence gaps.',
        'evidence-and-dependencies':'Upstream Research and Design contributions are synthetic examples. Preserve their exact versions and limits; confirm visit-type rules with clinic managers.',
        'design-consideration':'Never confirm a change before it is stored. Make the staff handoff explicit and tell the patient when to expect a reply.'}
    sections=[dict(id='new-package-'+kind, kind=kind, title=title, text=texts.get(kind,'Synthetic '+title.lower()+'.'),
                   rationale='Synthetic author guidance from the published intent and exact requirement.', disposition='use', requirement_ids=[]) for kind,title in BRIEF_ESSENTIALS.items()]
    for section in sections:
        if section['kind']=='validation':section['requirement_ids']=[r['ref']['id'] for r in row['body']['design_inputs']['requirements']]
    objective=dict(id='new-package-objective', title='Compare assistant concepts', question='Can a patient change an appointment without a phone call and know whether the change was stored?',
        why='Release slots early while keeping restricted visits with staff.', output='Comparable prototypes and a human research plan.', evidence='Actual patient sessions, counterexamples and implementation tests are still needed.')
    lee.command('domain-objectives-save',dict(expected=asdict(row['ref']), objectives=[objective], brief_sections=sections, complete=True))
    return lee.domain_brief.state()[0]


def knowledge(workspace, entries):
    # Entries: (kind, title, definition) or (kind, title, definition, extra). extra may name a parent
    # category or a relationship's subject and object by title, and give aliases. IDs depend on position,
    # so new entries are appended to keep earlier IDs stable.
    current=snapshot(workspace.store,workspace.domains.key)
    key=workspace.domains.key
    ids={entry[1]:'KN-'+hashlib.sha256((key+str(index)).encode()).hexdigest()[:12] for index,entry in enumerate(entries)}
    items=[]
    for index,entry in enumerate(entries):
        kind,title,definition=entry[:3]
        extra=entry[3] if len(entry)>3 else {}
        items.append(dict(id=ids[title], kind=kind, title=title, definition=definition,
            aliases=list(extra.get('aliases',[])), parent_id=ids.get(extra.get('parent',''),''),
            subject_id=ids.get(extra.get('subject',''),''), predicate=extra.get('predicate',''), object_id=ids.get(extra.get('object',''),''),
            source='Synthetic demonstration configuration; not organizational policy.', status='active',
            **{k:extra[k] for k in ('includes','excludes','not_confused_with','reach') if k in extra}))
    workspace.command('domain-knowledge-save',dict(domain=key, expected=current['ref'], entries=items, confirm_active=True, reason='Configure a clearly synthetic Riverbend Health demonstration.'))

def attach(workspace, thread, name, content):
    current=workspace.store.latest(thread['ref'].id, workspace.scopes)
    draft=workspace.domain_chat.draft(current)
    workspace.command('domain-chat-attach',dict(conversation=asdict(current['ref']), expected=asdict(draft['ref']),
        filename=name, content=base64.b64encode(content.encode()).decode()))
    return workspace.store.latest(thread['ref'].id, workspace.scopes)


def populate(store):
    result=seed_decision(store)  # The real intake → preflight → publication → issue → decision cycle.
    sam=Workspace(store,'sam',UnconfiguredModel())
    knowledge(sam,[('term','Observation','Record what was observed separately from interpretation and proposed action.'),
                   ('practice','Evidence limits','Qualitative findings need method, context, counterexamples and limits; sample count alone does not establish confidence.'),
                   ('practice','User-flow schematic','Map the current journey as a flow in FigJam; mark where people stop, wait or give up, and link each step to its evidence.'),
                   ('category','Research methods','How Research gathers and interprets evidence on this project.'),
                   ('category','Interviews','Conversations with patients and staff about recent appointments.',{'parent':'Research methods'}),
                   ('category','Journey mapping','Current-state flows that show where people stop, wait or give up.',{'parent':'Research methods'}),
                   ('term','Finding',"The researcher's supported synthesis of observations, with its scope and limits.",{'aliases':['synthesis','insight'],
                    'includes':'A stated source, method and limits.','excludes':'A single remark, or a pattern with no counterexamples sought.',
                    'not_confused_with':'Observation: what was seen or said, before any synthesis.','reach':'domain'}),
                   ('term','Counterexample','A case that contradicts or limits a pattern; it stays attached to the finding.'),
                   ('relationship','Observation informs Finding','A finding may synthesize observations while keeping their scope and limits.',{'subject':'Observation','predicate':'informs','object':'Finding'}),
                   ('relationship','Counterexample limits Finding','A counterexample narrows where a finding applies.',{'subject':'Counterexample','predicate':'limits','object':'Finding'})])
    researcher=sam.domain_chat.owned(sam.command('domain-chat-start',dict(title='Current rescheduling journey · scripted example'))['conversation'])
    researcher=attach(sam,researcher,'Riverbend-current-journey-figjam-synthetic.txt',NOTICE+'\n\n'+
        'Current-state user flow exported from FigJam (synthetic snapshot; no Figma retrieval occurred):\n'+FIGJAM_FLOW)
    user_flow=sam.command('domain-flow-save',dict(title='Current rescheduling journey (synthetic)',diagram=FIGJAM_FLOW))['flow']
    sam.domain_chat.turn(researcher,'user','Where in this flow do missed appointments actually come from?')
    sam.domain_chat.turn(researcher,'assistant','SCRIPTED DEMO, not live AI. In this synthetic flow, most missed appointments branch from "Call the clinic": office hours and holds stop people who already know they cannot attend. Forgetting is a separate, smaller path. Treat the counts as illustrative and look for counterexamples: patients who rescheduled successfully.')
    sam.domain_chat.turn(researcher,'user','What should I ask next to test that?')
    sam.domain_chat.turn(researcher,'assistant','SCRIPTED DEMO. Discussion guide: Tell me about the last appointment you could not make. When did you know? What did you try? What stopped you? What would have made changing it easy? Which visits would you not want an assistant to move? Ask front-desk staff which visit types need staff and why. Record observations, interpretations and counterexamples separately, then update the FigJam flow.')

    lee=Workspace(store,'lee',PrototypeFixture())
    knowledge(lee,[('term','Stored change','A change is confirmed only when the scheduling system has stored it; an offered slot is not a booking.'),
                   ('standard','Evaluate exact criteria','Review prototypes against published intent, released research and exact acceptance criteria. Static screens do not prove scheduling behavior or accessibility conformance.'),
                   ('practice','Figma prototypes','Generate comparable concepts into Figma through your connection, refine them there, and pull them back for evaluation.'),
                   ('category','Prototyping','How Design makes and compares concepts for this project.'),
                   ('category','Concept comparison','Several comparable concepts evaluated against the same criteria.',{'parent':'Prototyping'}),
                   ('term','Offered slot','A real open time the assistant shows the patient; it is not a booking until stored.',
                    {'includes':'Times the scheduling system reports as open at that moment.','excludes':'Waitlist positions and times held for another patient.',
                     'not_confused_with':'Stored change: a booking the scheduling system has confirmed.','reach':'project'}),
                   ('term','Staff handoff',"The assistant passes the request to staff with the patient's reason and preferred times retained.",{'aliases':['handoff']}),
                   ('relationship','Offered slot becomes Stored change','An offered slot becomes a stored change only after the scheduling system confirms it.',{'subject':'Offered slot','predicate':'becomes','object':'Stored change'}),
                   ('relationship','Staff handoff differs from Stored change','A handoff promises a staff reply, not a confirmed change.',{'subject':'Staff handoff','predicate':'differs from','object':'Stored change'})])
    design_brief=brief(lee)
    designer=lee.domain_chat.owned(lee.command('domain-chat-start',dict(title='Assistant concepts · prototype exploration'))['conversation'])
    designer=attach(lee,designer,'Riverbend-assistant-concepts-synthetic.txt',NOTICE+'\n\n'+
        'Compare A: reminder bot with confirm and cancel; B: conversational rescheduling agent; C: self-serve page with AI waitlist. Each covers start, exception and confirmed states. '
        'New-patient and procedure visits hand off to staff. Confirmation only after the change is stored. Screen specifications are proposals, not working software or human validation.')
    lee.domain_chat.turn(designer,'user','Compare these concepts against the revised intent, the released Research and the requirement criteria.')
    lee.domain_chat.turn(designer,'assistant','SCRIPTED DEMO, not live AI. A records confirmations but still needs a phone call to rebook, so it serves the original intent more than the revised one. B and C let patients release slots early. Both need the staff handoff and stored-only confirmation. Research suggests what to test; it does not pick a winner. Test with patients, and test slot availability through implementation.')
    draft=lee.domain_chat.draft(designer)
    values=dict(conversation=asdict(designer['ref']),expected=asdict(draft['ref']))
    preview=lee.command('domain-prototype-preview',values)
    prototype=lee.command('domain-prototype-generate',{**values,'signature':preview['signature'],'consent':True})
    lee.command('developer-brief-open',dict(conversation=asdict(designer['ref'])))
    developer=lee.developer_briefs.latest(designer)
    text=('SYNTHETIC DEVELOPER BRIEF: shared for review, not development approval.\n\n'
          'Purpose: let patients cancel or reschedule early without a phone call, so released time can be refilled.\n'
          'Behavior: offer only open slots; confirm only after the change is stored; keep the original appointment if a change fails; hand new-patient and procedure visits to staff with reason and preferred times; offer released slots to the waitlist; give no clinical advice.\n'
          'Design: compare the reminder bot, conversational agent and self-serve page with waitlist. No winning concept or real patient test is recorded.\n'
          'Acceptance: use the exact linked shared requirement and its criteria. Static screens do not establish scheduling behavior or accessibility.\n'
          'Evidence gaps: actual patient research, accessibility evaluation, scheduling-system integration tests, clinic-manager visit-type rules and measure baselines.\n'
          'Proposed backlog: eligible-visit rescheduling; staff handoff queue; stored-only confirmation; waitlist offer; clinical-question redirect. Review exact stories before staging Jira/ADO.\n'
          'All sources, persona actions and concepts in this package are synthetic. Publication does not authorize implementation or create external stories.')
    saved=lee.command('developer-brief-save',dict(conversation=asdict(designer['ref']),expected=asdict(developer['ref']),
        title='Appointment assistant: developer brief (synthetic)',text=text,source_refs=draft['body']['source_refs'],prototype=dict(id=prototype['id'],revision=1)))
    prepared=lee.command('developer-brief-prepare',dict(conversation=asdict(designer['ref']),expected=saved['ref']))
    handoff=store.latest(prepared['domainHandoff'],lee.scopes)
    published=lee.command('domain-publish',dict(expected=handoff['body']['draft'],preflight=asdict(handoff['ref']),confirm=True,release_sources=True))
    # Stage, but do not execute, local Jira/ADO simulations. The reviewer can complete them in the UI.
    owner=Workspace(store,'alex',UnconfiguredModel())
    issue=store.latest(result['issue']['id'],{SCOPE})
    previews={target:owner.command('demo-delivery-prepare',dict(issue=asdict(issue['ref']),target=target))['demoDeliveryPreview'] for target in ('jira','ado')}
    result.update(package_version=1, research_conversation=asdict(researcher['ref']), user_flow=user_flow,design_conversation=asdict(designer['ref']),
        design_brief=asdict(design_brief['ref']), prototype=dict(id=prototype['id'],revision=1), developer_brief=saved['ref'],
        developer_shared=asdict(lee.developer_briefs.state()['shared'][0]['ref']), developer_packet=published['packet'], delivery_previews=previews)
    store.put(MARKER,'demo-package',SCOPE,result)
    return result


def verify(store):
    manifest=store.latest(MARKER,{SCOPE})['body']
    if manifest.get('package_version')!=1:raise ValueError('This saved demo has an unsupported format; its data was not changed.')
    requirement=store.read(reference(manifest['requirement_after']),{SCOPE})
    if requirement['body']['status']!='approved' or 'hand the request to staff' not in requirement['body']['text']:
        raise ValueError('The approved demonstration requirement is missing.')
    intent=store.latest('INT-001',{SCOPE})
    if intent['ref'].revision<2 or store.read(reference(manifest['intent_before']),{SCOPE})['body']['intake']['need']==intent['body']['intake']['need']:
        raise ValueError('The revised business intent is missing.')
    checks=['published business intent','business intent revised from a published finding, original retained','goals and KPIs','requirement drawers and acceptance criteria','Research and Design source versions']
    for key in ('sponsor_published','research','design_initial','design_revised','result'):
        raw=manifest['packets'][key]
        packet=store.resolve_packet(raw['id'],raw['revision'],{SCOPE})
        if not packet['records'] or any(r['scope']!=SCOPE for r in packet['records']):
            raise ValueError('A shared context packet has invalid scope.')
    checks+=['exact historical evidence trail','bridge discussion and human decision','versioned requirement change']
    graph=store.graph({SCOPE})
    if reference(manifest['requirement_after']) not in graph:
        raise ValueError('The requirement graph cannot be rebuilt.')
    for actor,key in [('sam','research_conversation'),('lee','design_conversation')]:
        workspace=Workspace(store,actor,UnconfiguredModel())
        if not workspace.domain_chat.turns(workspace.domain_chat.owned(manifest[key],current=False)):
            raise ValueError('A domain walkthrough is missing.')
    flows=Workspace(store,'sam',UnconfiguredModel()).flows.state()['flows']
    if not any(f['ref'].id==manifest['user_flow']['id'] for f in flows):raise ValueError('The Research user flow is missing.')
    developer=store.read(reference(manifest['developer_shared']),{SCOPE})
    if developer['body']['status']!='shared-for-review':raise ValueError('Developer brief review state is invalid.')
    checks+=['rebuildable dependency graph','Research user flow ready for FigJam','domain configuration and scripted discussions','configured Design and Developer briefs','Jira/ADO staged simulation previews']
    return dict(checks=checks,manifest=manifest)


def initialize(path):
    """Publish a completely seeded new file; never seed/reset an existing store."""
    path=Path(path).resolve()
    if path.exists():
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            try:owned=db.execute('SELECT 1 FROM records WHERE id=?',(MARKER,)).fetchone()
            except sqlite3.DatabaseError:owned=None
        if not owned:raise ValueError('The selected database is not a packaged demo. It was not changed.')
        with closing(Store(path)) as store:return verify(store)
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,raw=tempfile.mkstemp(prefix='.building-',suffix='.sqlite3',dir=path.parent)
    os.close(fd);temporary=Path(raw)
    try:
        with closing(Store(temporary)) as store,store.transaction():
            populate(store)
            report=verify(store)
        os.link(temporary,path)  # Atomic no-overwrite publication on the same filesystem.
        return report
    finally:
        temporary.unlink(missing_ok=True)


def workflow_check():
    """Run against disposable data; never exercise mutations on the saved demo."""
    from .web import BrowserServer
    with tempfile.TemporaryDirectory(prefix='workbench-demo-check-') as tmp:
        path=Path(tmp)/'workbench.sqlite3';report=initialize(path)
        server=BrowserServer(('127.0.0.1',0),path,UnconfiguredModel(),development=True,workspace_notice=NOTICE_TEXT)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=30)
        cookie='';state={}
        def request(method,url,payload=None):
            nonlocal cookie,state
            headers={'Cookie':cookie}
            if payload is not None:headers.update({'Content-Type':'application/json','X-CSRF-Token':state['csrf'],'X-Workbench-Project':'original','X-Workbench-Version':'1'})
            conn.request(method,url,body=json.dumps(payload) if payload is not None else None,headers=headers)
            response=conn.getresponse();raw=response.read()
            if response.getheader('Set-Cookie'):cookie=response.getheader('Set-Cookie').split(';')[0]
            data=json.loads(raw) if 'application/json' in response.getheader('Content-Type','') else raw
            return response.status,data
        try:
            status,state=request('GET','/api/state')
            if status!=200:raise AssertionError(state)
            for asset in ('/','/project-flow.js','/domain-chat.js','/bridge.js','/workspace.css','/inter-latin.woff2'):
                if request('GET',asset)[0]!=200:raise AssertionError('Missing packaged asset: '+asset)
            for actor in ('priya','sam','lee','alex'):
                if request('POST','/api/profile',{'actor':actor})[0]!=200:raise AssertionError(actor)
                status,state=request('GET','/api/state')
                if status!=200 or state['actor']!=actor:raise AssertionError('Profile state failed: '+actor)
                if state['project_flow']['can_request']:raise AssertionError('Task dispatch must remain retired.')
                if actor!='lee' and state['developer_briefs']['private']:raise AssertionError('Private Design brief leaked.')
                if actor=='sam' and request('POST','/api/developer-brief-read',dict(ref=report['manifest']['developer_brief']))[0]!=403:
                    raise AssertionError('Research could read a private Design brief.')
                if actor=='lee':
                    conversation=next(t for t in state['domain_chat']['threads'] if t['ref']['id']==report['manifest']['design_conversation']['id'])
                    draft=next(r for r in state['records'] if r['ref']['id']==conversation['body']['draft_id'])
                    status,attached=request('POST','/api/domain-chat-attach',dict(conversation=conversation['ref'],expected=draft['ref'],filename='private-check.txt',content=base64.b64encode(b'PRIVATE UPLOAD NOT SELECTED FOR PUBLICATION').decode()))
                    if status!=200:raise AssertionError(attached)
                    status,state=request('GET','/api/state')
                    row=state['developer_briefs']['private'][0]
                    values=dict(conversation=attached['conversation'],expected=row['ref'],title=row['body']['title'],text=row['body']['text']+'\nSynthetic follow-up: explicit author edit.',source_refs=row['body']['source_refs'],prototype=row['body']['prototype']['ref'])
                    status,saved=request('POST','/api/developer-brief-save',values)
                    if status!=200:raise AssertionError(saved)
                    status,prepared=request('POST','/api/developer-brief-prepare',dict(conversation=attached['conversation'],expected=saved['ref']))
                    if status!=200:raise AssertionError(prepared)
                    status,state=request('GET','/api/state')
                    handoff=next(h for h in state['domains']['handoffs'] if h['ref']['id']==prepared['domainHandoff'])
                    status,published=request('POST','/api/domain-publish',dict(expected=handoff['body']['draft'],preflight=handoff['ref'],confirm=True,release_sources=True))
                    if status!=200:raise AssertionError(published)
                    with closing(Store(path)) as inspected:
                        packet=inspected.resolve_packet(published['packet']['id'],published['packet']['revision'],{SCOPE})
                        if 'PRIVATE UPLOAD NOT SELECTED' in str(packet):raise AssertionError('Unselected upload leaked into the shared packet.')
                    report['checks']+=['HTTP text upload, brief editing, preflight and repeat publication']

            for target in ('jira','ado'):
                preview=report['manifest']['delivery_previews'][target]
                status,receipt=request('POST','/api/demo-delivery-commit',dict(expected=dict(id=preview,revision=1),confirm_demo=True))
                if status!=200:raise AssertionError(receipt)
                status,state=request('GET','/api/state')
                receipts=state['demo_delivery']['receipts']
                if not any(r['body']['mode']=='simulated' and r['body']['target']==target and r['body']['external_request_sent'] is False for r in receipts):raise AssertionError('Simulation receipt missing.')
            if request('POST','/api/work-request-create',{})[0]!=400:raise AssertionError('Retired assignment API is still enabled.')
        finally:
            conn.close();server.shutdown();server.server_close();thread.join()
        with closing(Store(path)) as store:
            shared=store.resolve_packet(report['manifest']['developer_packet']['id'],report['manifest']['developer_packet']['revision'],{SCOPE})
            if any(r['scope']!=SCOPE for r in shared['records']):raise AssertionError('Developer packet privacy failed.')
            receipt=Workspace(store,'sam',UnconfiguredModel()).bridge.state()['issues'][0]['decision_receipt']
            if not receipt['available']:raise AssertionError('Decision receipt unavailable after reopening.')
        report['checks']+=['HTTP UI/assets and all four personas','backend-enforced domain privacy','Jira and ADO simulation receipts','retired assignment command','database reopen and decision receipt']
        return report['checks']


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir',type=Path,required=True)
    parser.add_argument('--port',type=int,default=8770)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    if args.check:
        checks=workflow_check()
        print(json.dumps(dict(status='passed',checks=checks,external_model_calls=0,external_writes=0),indent=2))
        return 0
    from .web import BrowserServer
    path=args.data_dir.resolve()/'workbench.sqlite3'
    try:
        report=initialize(path)
        from .model_connection import ModelConnections
        connection=ModelConnections(args.data_dir.resolve().parent/'model-connections.json')
        def notice():
            return ('Synthetic Riverbend Health demo · AI configured for real requests · Jira/ADO simulated'
                    if connection.effective('original')['configured'] else NOTICE_TEXT)
        server=BrowserServer(('127.0.0.1',args.port),path,development=True,workspace_notice=notice,model_connection=connection)
    except (OSError,ValueError) as error:
        parser.exit(1,str(error)+'\nTry --port 8771 if the port is occupied. Saved data was not reset.\n')
    print('\nAdaptive Cointelligence demo: http://127.0.0.1:'+str(server.server_port)+'/',flush=True)
    print(notice(),flush=True)
    print('Saved demo data: '+str(path),flush=True)
    print('Walkthrough: docs/demo.md. Ctrl+C stops the server; run the same command to resume.\n',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nStopped. Demo changes remain saved.')
    finally:server.server_close()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
