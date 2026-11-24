"""Explicit fictional packet-crossing fixture; never selected as a runtime model.

A scripted model and seeded project used only by the tests.
Creates an isolated project; preserves existing projects and uses no external service.
"""
import argparse
from contextlib import closing
from dataclasses import asdict
from pathlib import Path
import json

from workbench.core import Store
from workbench.decisions import SCOPE, now
from workbench.domain import EDITABLE
from workbench.projects import Projects
from workbench.workspace import Workspace
from workbench.domain_knowledge import seed_fictional_knowledge, entry

PROJECT_ID='demo-domain-interpretation-v2'
MARKER_ID='DEMO-DOMAIN-INTERPRETATION'
TITLE='Clinic · domain setup & interpretation (fictional)'
NOTICE='All people, source notes, assessments and proposals in this walkthrough are fictional. No live model, user research, conformance evaluation or external update was run.'


class FictionalInterpretationModel:
    """A named scenario fixture, only injected by this seeder and tests."""
    def status(self):return dict(configured=True,provider='Fictional scenario fixture',model='not-a-live-model')
    def generate(self,*,instructions,context,schema):
        if context['skill']!='domain-packet-interpretation':raise AssertionError('Fixture supports only packet interpretation')
        c=context
        def evidence(text):
            return next(e['id'] for e in c['excerpts'] if text in e['quote'])
        req=c['requirements'][0]['ref']['id']
        if c['domain']=='research':
            primary=evidence('Assumption: every initial report needs a photo')
            summary='Research separates the sponsor’s photo assumption from the user need and defines what must be investigated.'
            applications=[dict(knowledge_id='vocabulary',application='Treat “photo required” as a proposed solution, not an established user need.',evidence_ids=[primary]),dict(knowledge_id='evidence_standard',application='The intake contains an assumption, not an observed research result; no prevalence or benefit is established.',evidence_ids=[primary]),dict(knowledge_id='authority',application='Investigate the assumption without approving a change to the shared requirement.',evidence_ids=[primary])]
            findings=[dict(kind='gap',title='The photo gate has no supporting task evidence',detail='The fictional intake assumes a photo is needed before capture. Research must establish when evidence is available and whether capture and closure have different needs.',question='At what point does the receptionist need a photo, and what must triage know before closure?',knowledge_ids=['vocabulary','evidence_standard'],evidence_ids=[primary],requirement_ids=[req],route='domain'),dict(kind='question',title='Runtime value has no baseline',detail='Completion and evidence-complete closure are candidate measures. No measured baseline, target or financial value is supplied.',question='Who owns measuring completed submissions and evidence-complete closure in a bounded pilot?',knowledge_ids=['evidence_standard'],evidence_ids=[evidence('Baseline and target unknown')],requirement_ids=[],route='coordination')]
        else:
            capture=next(r['ref']['id'] for r in c['requirements'] if 'confirmation' in r['body']['text'])
            primary=evidence('three of six invented task sessions')
            summary='Design translates a bounded Research finding into an interruption-and-recovery hypothesis, preserving its limits and the requirement for confirmed storage.'
            applications=[dict(knowledge_id='vocabulary',application='A finding about interrupted photo capture supports exploration of staged evidence; it does not prove a particular save mechanism.',evidence_ids=[primary]),dict(knowledge_id='evidence_standard',application='Keep the six fictional sessions as illustrative qualitative context; do not extrapolate to a runtime KPI or conformance result.',evidence_ids=[primary]),dict(knowledge_id='criterion-3',application='Specify offline, failed-upload and resume states. Successful submission still requires a storage acknowledgement.',evidence_ids=[evidence('confirmation only after storage acknowledgement')])]
            findings=[dict(kind='conflict',title='Immediate success feedback conflicts with confirmed storage',detail='Research proposes immediate reassurance during interruption. Displaying a submitted state before storage acknowledgement would contradict the governing capture requirement. A proposed “saved on device / awaiting sync” state needs review.',question='Can we distinguish local draft retention from confirmed submission, and retain entered work until synchronization succeeds?',knowledge_ids=['criterion-3','vocabulary'],evidence_ids=[primary,evidence('confirmation only after storage acknowledgement')],requirement_ids=[capture],route='requirement'),dict(kind='gap',title='Recovery and accessibility evidence are missing',detail='The research excerpt does not establish keyboard, screen-reader or interrupted-upload behavior. Design must define and test those states before claiming they work.',question='Which recovery states and applicable accessibility criteria should the prototype test cover?',knowledge_ids=['evidence_standard','criterion-3'],evidence_ids=[primary],requirement_ids=[capture],route='domain')]
        structured=[k for k in c['knowledge'] if k['kind']=='domain-reviewed-guidance']
        if structured:
            chosen=next((k for k in structured if 'Local draft' in k['title']),structured[0])
            applications.append(dict(knowledge_id=chosen['id'],application='Apply this reviewed local definition while preserving the distinction between hypothetical evidence, retained work and a verified outcome.',evidence_ids=[primary]))
            findings[0]['knowledge_ids'].append(chosen['id'])
        return dict(output=dict(summary=summary,applications=applications,findings=findings,limitations=NOTICE+' Standards shown are configured guidance; no website or external policy was retrieved.'),model='fictional-fixture',usage=None)


def seed_extra_domain(store,marker):
    """Explicitly requested domain-setup demo; never touches another project."""
    admin=Workspace(store,'administrator',admin=True);key='support-readiness-fictional'
    if any(d['key']==key for d in admin.domain_knowledge.definitions()):return key
    admin.command('domain-add',dict(label='Support readiness (fictional)',purpose='Prepare support guidance for the fictional non-safety feedback workflow.',members=['sam','lee'],leaders=['sam'],template='research'))
    w=Workspace(store,'sam',domain_key=key)
    a=entry('term','Pending report','A retained report that is not yet confirmed as stored by the service.','Fictional domain-lead example; not an operational policy.')
    b=entry('term','Support instruction','Guidance that explains pending, retry and confirmed states without promising unavailable behavior.','Fictional domain-lead example; not a verified support procedure.')
    rel=entry('relationship','Support depends on state meaning','Instructions must distinguish a local draft from a confirmed report.','Fictional support-readiness example.')
    rel.update(subject_id=b['id'],predicate='depends-on',object_id=a['id'])
    w.command('domain-knowledge-save',dict(domain=key,expected=None,entries=[a,b,rel],reason='Clearly fictional example of a configured additional domain.',confirm_active=True))
    reqs=marker['requirements'];task=Workspace(store,'priya').project_flow.seed_legacy_request(dict(title='Prepare support readiness (fictional)',recipient='sam',recipient_domain=key,objective='Identify what support needs to explain interrupted reporting safely.',local_context='Apply the configured support glossary and preserve Research uncertainty.',expected_output='A source-linked support gap or proposed instruction.',packet_refs=[marker['research_packet']],requirement_refs=reqs,requirement_guidance=[dict(ref=r,local_application='Identify what this means for support communication.',expected_evidence='Proposed guidance with source and unresolved dependencies.') for r in reqs]))
    w.command('work-request-start',dict(expected=dict(id=task['id'],revision=1)))
    return key


def populate(store):
    if store.db.execute('SELECT 1 FROM records LIMIT 1').fetchone():raise ValueError('Use a new empty store for the fictional crossing')
    model=FictionalInterpretationModel();work={a:Workspace(store,a,model) for a in ('alex','priya','sam','lee')};owner=work['alex']
    owner.setup(dict(title=TITLE,intent='Capture non-safety operational feedback promptly while retaining accountable, evidenced resolution.',boundary='Fictional non-safety workflow only; excludes clinical care, billing and incident reporting.'))
    reqs=[]
    for title,text,ac in [('Reliable capture','Preserve report content through interrupted uploads; show submission confirmation only after storage acknowledgement.','A failed upload retains entered content. A pending state differs from confirmed submission.'),('Staged evidence','Assumption: every initial report needs a photo before submission; require evidence or a named exception before closure.','Capture and closure evidence needs must be reviewed with Research and Design.')]:
        result=owner.create_requirement(dict(title=title,text=text,rationale='Fictional candidate linked to intent; not an approved policy.',conditions='Non-safety prototype only',drawer='Experience and usability',acceptance_criteria=ac));reqs.append(store.latest(result['id'],{SCOPE})['ref'])
    goal=store.put('GOAL-FICTIONAL','goal',SCOPE,dict(title='Usable feedback without lost work',outcome='Capture relevant detail without avoidable interruption.',status='candidate'))
    measure=store.put('MEASURE-FICTIONAL','success-measure',SCOPE,dict(title='Completed submissions and evidence-complete closures',definition='Separate submission completion from closure quality. Baseline and target unknown; assign an owner before pilot.',status='candidate'))
    business=dict(id='PKT-DEMO-BUSINESS',revision=1)
    store.packet(business['id'],1,'Fictional business intent and build expectations',[store.latest('INT-001',{SCOPE})['ref'],store.latest('POL-001',{SCOPE})['ref'],*reqs,goal,measure],{SCOPE},{SCOPE})
    # A reusable domain preset with a recorded local override, not an enterprise policy.
    for a in ('sam','lee'):
        w=work[a];p=w.domains.profile();config={k:p['config'][k] for k in EDITABLE}
        config['evidence_standard']+=' Fictional demo requirement: preserve evidence limits and identify missing applicable standard sources; this is not certified policy.'
        w.command('domain-configure',dict(domain=w.domains.key,expected=p['ref'],config=config,reason='Explicit fictional domain-crossing walkthrough.'))
    seed_fictional_knowledge(work)
    research=work['sam'];report=research.command('domain-interpretation-assess',dict(packet=business,consent=True))
    rreport=research.domain_interpretation.reports()[0]
    task=work['priya'].project_flow.seed_legacy_request(dict(title='Investigate interrupted report capture (fictional)',recipient='sam',objective='Separate the user need from the mandatory-photo assumption.',expected_output='A bounded finding with evidence limits and implications for Design.',local_context='Apply Research evidence standards. Study triggers, actions, obstacles and desired outcomes.',boundaries='Fictional non-safety example.',requirement_guidance=[dict(ref=asdict(r),local_application='Examine the reporting task and evidence timing.',expected_evidence='Attributable observation, limits and unresolved questions.') for r in reqs],packet_refs=[business],requirement_refs=[asdict(r) for r in reqs]))
    start=research.command('work-request-start',dict(expected=dict(id=task['id'],revision=1)));draft=store.latest(start['id'],research.scopes)
    research.command('domain-save',{**draft['body'],'expected':asdict(draft['ref']),
        'observation':'Fictional finding: three of six invented task sessions paused at photo capture; two resumed and one abandoned the draft. No real study was conducted.',
        'interpretation':'Evidence collection may interrupt capture. Distinguish report capture from evidence needed before closure.',
        'recommendation':'Explore staged evidence and immediate reassurance during interruption; Design must define what is stored locally versus on the server.',
        'source':'Fictional session notes v1; authored solely for this walkthrough.','limitation':'Six invented sessions are not empirical evidence. No population estimate, preferred solution or runtime KPI effect is established.',
        'links':draft['body']['links'],'source_refs':[]})
    draft=store.latest(draft['ref'].id,research.scopes)
    prepared=research.command('domain-prepare',dict(expected=asdict(draft['ref']),recipient='design',intent_implications='Re-examine the mandatory-photo gate; preserve reliable capture.',downstream_needs='Design interruption, recovery, pending and confirmed states.',open_questions='Storage acknowledgement and accessibility testing remain to be specified.'))
    handoff=store.latest(prepared['domainHandoff'],research.scopes)
    shared=research.command('domain-publish',dict(expected=asdict(draft['ref']),preflight=asdict(handoff['ref']),confirm=True,release_sources=False,release_interpretations=True))
    design=work['lee'];dreport=design.command('domain-interpretation-assess',dict(packet=shared['packet'],consent=True));dr=design.domain_interpretation.reports()[0]
    design.command('domain-chat-start',dict(title='Staged evidence prototype (fictional)'))
    issue=design.command('domain-interpretation-bridge',dict(expected=asdict(dr['ref']),index=0,route='requirement',target=asdict(reqs[0]),owner='lee',boards=['research-design','business-design'],confirm=True))
    marker=dict(fictional=True,title=TITLE,notice=NOTICE,business_packet=business,research_interpretation=dict(id=report['interpretationResult'],revision=1),research_packet=shared['packet'],design_interpretation=dict(id=dreport['interpretationResult'],revision=2),issue=dict(id=issue['bridgeIssue'],revision=1),requirements=[asdict(r) for r in reqs],evaluation='scripted-fixture-not-live-model')
    store.put(MARKER_ID,'demo-domain-interpretation',SCOPE,marker)
    seed_extra_domain(store,marker)
    return marker


def seed_project(anchor):
    projects=Projects(anchor)
    with projects.db() as db:existing=db.execute('SELECT * FROM projects WHERE id=?',(PROJECT_ID,)).fetchone()
    if existing:
        with projects.locked(PROJECT_ID) as p:
            with closing(Store(p['path'])) as store:return store.latest(MARKER_ID,{SCOPE})['body']
    path=projects.new_path()
    try:
        with closing(Store(path)) as store:
            with store.transaction():result=populate(store)
        with projects.db() as db:db.execute('INSERT INTO projects VALUES (?,?,?,?)',(PROJECT_ID,str(path),1,now()))
    except Exception:
        path.unlink(missing_ok=True);raise
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--db',required=True,type=Path);args=parser.parse_args()
    if not args.db.is_file():parser.error('Choose an existing local Workbench anchor database')
    print(json.dumps(seed_project(args.db),indent=2))

if __name__=='__main__':main()
