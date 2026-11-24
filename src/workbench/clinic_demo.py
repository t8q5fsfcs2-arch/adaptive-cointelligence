"""Riverbend Health: an isolated, replayable synthetic adaptive-intent walkthrough.

A sponsor proposes an AI appointment assistant. Research and Design do their own
consequential work. A research finding revises the business intent through the
sponsor's explicit decision, then a Design dependency is resolved through an
authorized requirement decision.

Uses the real intake, preflight, packet, refinement, issue, review and decision
services. No client data, model evaluation or external writes are used. Existing
projects are never seeded or reset; the new store is complete before registration.
Run: python -m workbench.clinic_demo --db data/workbench.sqlite3
"""
import argparse
from contextlib import closing
from dataclasses import asdict
import json
from pathlib import Path

from .core import Ref, Store
from .decisions import SCOPE, now
from .projects import Projects
from .workspace import Workspace

PROJECT_ID = 'demo-riverbend-appointment-assistant-v1'
MARKER_ID = 'DEMO-RIVERBEND-APPOINTMENT-ASSISTANT'
TITLE = 'Riverbend Health · AI appointment assistant (synthetic demo)'
NOTICE = ('Synthetic walkthrough. Riverbend Health, its patients and staff, all '
          'observations, sources, dialogue and persona decisions were authored for '
          'this demo. No interviews, prototype sessions, FigJam or Figma retrievals '
          'or AI assessments were performed. Not clinical or operational policy.')
BOUNDARY = ('Scheduling and communication for routine outpatient appointments only. '
            'The assistant gives no clinical advice, symptom triage, prescription or '
            'emergency guidance; it directs those to staff or emergency services. '
            'Synthetic data only; no patient records, scheduling-system integration '
            'or clinical authorization.')
INITIAL = ('The AI appointment assistant sends a text reminder 72 hours and 24 hours '
           'before each appointment and asks the patient to confirm attendance by reply.')
REVISED = ('Let patients cancel or reschedule through the AI appointment assistant at '
           'any time before the appointment, by text or chat. For eligible routine '
           'visit types, offer real open slots and confirm the change only after the '
           'scheduling system stores it. For new-patient and procedure visits, hand '
           'the request to staff with the patient\'s reason and preferred times '
           'retained, and tell the patient when to expect a reply. Offer each released '
           'slot to the clinic waitlist. Never give clinical advice.')
CRITERIA = ('1. A patient can cancel or reschedule an eligible routine visit from a '
            'reminder without a phone call; the assistant offers only slots the '
            'scheduling system reports as open.\n'
            '2. Confirmation appears only after the change is stored; a failed change '
            'keeps the original appointment and explains the next step.\n'
            '3. New-patient and procedure requests reach staff with the reason and '
            'preferred times retained; the patient is told the expected reply time.\n'
            '4. A released slot is offered to the waitlist and the refill is recorded.\n'
            '5. Clinical questions are directed to staff or emergency services. These '
            'criteria have not been tested.')
NEED_V1 = ('Patients forget appointments; 18% of booked visits are missed, leaving '
           'clinician time unused and delaying care for others. Initial hypothesis.')
NEED_V2 = ('Most patients who miss appointments already know they cannot attend, but '
           'rescheduling requires a phone call during business hours. Their slot is '
           'released too late, or never, to be refilled. Forgetting is a smaller share.')
CHALLENGE_V1 = ('Synthetic investment hypothesis: missed appointments cost an estimated two '
                'clinician-days per clinic each week because patients forget them. The financial '
                'benefit is not established.')
CHALLENGE_V2 = ('Synthetic investment hypothesis: missed appointments cost an estimated two '
                'clinician-days per clinic each week. Most are known in advance but cannot be '
                'changed easily, so the time is released too late to refill. The financial '
                'benefit is not established.')
PAIN_V2 = ('Changing an appointment needs a phone call during office hours, with long holds.\n'
           'Slots released late are rarely refilled.\n'
           'Some visit types need staff to move them, and patients do not trust an AI with those.')
APPROACH_V1 = ('An AI assistant that sends text reminders and asks patients to confirm '
               'attendance by reply.')
APPROACH_V2 = ('An AI assistant that makes it easy to cancel or reschedule early, by text '
               'or chat, hands restricted visit types to staff, and refills released '
               'time from the waitlist. Reminders remain part of the service.')
FIGJAM_FLOW = '''flowchart LR
  A[Reminder text arrives] --> B{Can the patient attend?}
  B -- Yes --> C[Reply to confirm]
  B -- No --> D[Call the clinic]
  D --> E{Office open?}
  E -- No --> F[Plan to call later]
  F --> G[Forgets or gives up]
  G --> H[Missed appointment: slot unused]
  E -- Yes --> I[Average 11 minute hold]
  I --> J{Stays on hold?}
  J -- No --> G
  J -- Yes --> K[Front desk reschedules]
  K --> L[Slot released late: rarely refilled]'''


class NoEvaluation:
    def status(self):
        return dict(configured=False, provider='Synthetic walkthrough; no evaluation', model='')

    def generate(self, **kwargs):
        raise AssertionError('This synthetic walkthrough must never call a model')


def complete_design_brief(w, draft):
    from .domain_brief import BRIEF_ESSENTIALS
    if w.domains.key != 'design':
        return None
    existing = w.domain_brief.readiness(draft)
    if existing['ready']:
        return w.store.read(Ref(**existing['brief']), w.scopes)
    w.command('domain-brief-create', dict(work_request=draft['body'].get('work_request')))
    r = w.domain_brief.state()[0]
    reqs = r['body']['design_inputs']['requirements']
    sections = [dict(id='new-'+kind, kind=kind, title=title, text='Synthetic author-defined '+title.lower()+'.',
                     rationale='A synthetic lifecycle fixture, not operational guidance.', disposition='use',
                     requirement_ids=[]) for kind, title in BRIEF_ESSENTIALS.items()]
    for section in sections:
        if section['kind'] == 'validation':
            section['requirement_ids'] = [v['ref']['id'] for v in reqs]
    objective = dict(id='new-objective', title='Validate the assistant concepts',
                     question='Can a patient change an appointment without a phone call?',
                     why='Tests the revised intent.', output='Comparable prototypes and a review.',
                     evidence='Synthetic task evidence.')
    w.command('domain-objectives-save', dict(expected=asdict(r['ref']), objectives=[objective],
                                             brief_sections=sections, complete=True))
    return w.domain_brief.state()[0]


def revised_framing(draft, statement, solution, risk):
    """The sponsor's framing after a revision: same name and context, revised problem, approach and risk."""
    framing = dict(draft['body'].get('sponsor_brief', {}).get('framing', {}))
    summary = dict(framing.get('summary') or {})
    summary.update(problem=statement, solution=solution, risk=risk)
    return dict(name=framing.get('name') or draft['body']['title'], context=framing.get('context', ''), statement=statement, summary=summary)


def populate(store):
    """Populate only a new empty store, using the normal workflow commands."""
    if store.db.execute('SELECT 1 FROM records LIMIT 1').fetchone():
        raise ValueError('The synthetic walkthrough requires a new empty project store')
    work = {actor: Workspace(store, actor, NoEvaluation()) for actor in ('priya', 'sam', 'lee', 'alex')}
    sponsor = work['priya']; intake = sponsor.intake

    def latest(id):
        return store.latest(id, sponsor.scopes | work['sam'].scopes | work['lee'].scopes)

    def ref(id):
        return asdict(latest(id)['ref'])

    def intake_ref():
        return asdict(intake.draft()['ref'])

    # 1. The sponsor states the starting business intent.
    sponsor.command('intake-start', dict(title=TITLE))
    profile = intake.profile()
    sponsor.command('intake-configure', dict(expected=asdict(profile['ref']),
        name='Riverbend Health · Research + Design', drawers=profile['body']['drawers']))
    values = dict(
        beneficiaries='Patients of Riverbend Health\'s six outpatient clinics and the front-desk teams who schedule them (synthetic).',
        jobs='Attend booked appointments, or change them early when plans change; keep clinician time in use.',
        need=NEED_V1,
        gains='Fewer missed visits, shorter waits for appointments and less front-desk phone time.',
        approach=APPROACH_V1,
        job_support='Send timely reminders by text and capture confirmations without staff effort.',
        pain_relievers='Remind patients early enough to act; avoid adding phone work for the front desk.',
        gain_creators='Show the clinic which appointments are confirmed so staff can plan the day.',
        value='Reduce missed appointments so clinician time is used and patients wait less for care.',
        business_challenge=CHALLENGE_V1,
        why_now='The current reminder system is end-of-life this year; choose the replacement on evidence.',
        measures='Missed-appointment rate (baseline 18%, target 10% within two quarters, synthetic); confirmation reply rate.',
        evidence=NOTICE,
        assumptions='Patients miss appointments mainly because they forget; an AI reminder that asks for confirmation will fix it. Research and Design must challenge both assumptions.',
        assumption_owner='sam',
        supporting_users='Front-desk schedulers and clinic managers (synthetic).')
    sponsor.command('intake-save', dict(expected=intake_ref(), step='value', **values))
    sponsor.command('intake-accept-value', dict(expected=intake_ref(), confirm=True,
        rationale='Synthetic sponsor review of the starting value hypothesis, not validation or delivery approval.'))
    context = dict(in_scope='Appointment reminders, confirmation, cancellation and rescheduling for routine outpatient visits.',
        out_scope=BOUNDARY, constraints=BOUNDARY,
        sources='Only the explicitly synthetic source notes authored inside this sample project.',
        open_questions='Why do patients miss appointments, and what would let a released slot be refilled? No actual patient or scheduling data collected.',
        work_kind='digital',
        user_situation='Synthetic patients receive texts on their phones; many work shifts and cannot call during office hours.',
        research_question='Why do patients miss appointments, and what happens when they know they cannot attend?',
        operations_question='Which visit types can be changed without staff, and who handles the rest?',
        user_actions='Read a reminder; confirm, cancel or reschedule; ask a question; get a new time.',
        bottlenecks='Initial assumption: patients forget their appointments.',
        tools='A proposed AI text and chat assistant; no live scheduling system connected.',
        handoffs='Assistant to front desk; Research findings to Design; consequential questions to Decisions & Issues.',
        desired_outputs='Kept appointments, early changes and refilled slots, with the patient told what happened.',
        dependencies='Real-time open-slot data, visit-type rules and a staff handoff queue must be designed and tested.')
    sponsor.command('intake-save', dict(expected=intake_ref(), step='context', **context))
    goal = dict(id='G-appointment-access', title='Use clinician time and shorten waits for care',
        outcome='Fewer appointments go unused and patients get seen sooner.',
        beneficiary=values['beneficiaries'], rationale='Missed appointments waste capacity; the cause is a hypothesis to test.',
        owner='Dana Okafor · synthetic business sponsor', active=True, basis_fields=['value', 'jobs', 'gains'])
    measures = [dict(id='M-missed-rate', name='Missed-appointment rate',
            definition='Booked appointments not attended and not changed before start time, divided by booked appointments, per clinic per month.',
            population='All routine outpatient appointments in the synthetic pilot clinics.',
            data_source='Proposed scheduling-system attendance export; not implemented or evaluated.',
            owner='Dana Okafor · synthetic measurement owner', guardrail='Do not reduce the rate by discouraging bookings or hiding late cancellations.',
            review_plan='Confirm the baseline and target with clinic managers before a real pilot.',
            goal_ids=['G-appointment-access'], active=True, basis_fields=['measures']),
        dict(id='M-confirm-rate', name='Confirmation reply rate',
            definition='Reminders answered with a confirmation, divided by reminders sent.',
            population='Reminders sent in the synthetic pilot.',
            data_source='Proposed assistant message log; not implemented.',
            owner='Sofia Alvarez · synthetic requirement owner', guardrail='Confirmation is not attendance; report both.',
            review_plan='Compare with attendance before treating replies as success.',
            goal_ids=['G-appointment-access'], active=True, basis_fields=['measures'])]
    sponsor.command('goals-save', dict(expected=intake_ref(), goals=[goal], measures=measures))
    sponsor.command('sponsor-save', dict(expected=intake_ref(), answers={
        'q8': dict(items=['Front desk: "Most of our day is answering calls to move appointments."',
                          'Patients: "I knew on Monday I could not make Thursday, but I could not get through."']),
        'q10': dict(items=['Never confirm a change the scheduling system has not stored.',
                           'Never give clinical advice; direct clinical questions to staff or emergency services.',
                           'Always let a patient reach a person.']),
        'q11': dict(items=['If the assistant cannot tell what the patient wants, it asks one clarifying question, then offers a call back from staff.']),
        'q12': dict(items=['No open slot fits: offer the waitlist and a staff call back; the front-desk lead owns follow-up.',
                           'The scheduling system is unavailable: keep the original appointment and tell the patient; IT on call owns recovery.']),
        'q13': dict(items=['Patients with several appointments the same day.', 'Caregivers acting for a patient.',
                           'Patients who reply in a language other than English.']),
        'q18': dict(items=['Monthly, in the patient-access review, by clinic.']),
        'q20': dict(items=['Synthetic data only; no patient records, scheduling-system integration or clinical authorization in this pilot.'])}))
    sponsor.command('intake-build', dict(expected=intake_ref()))
    drawers = intake.draft()['body']['scaffold']
    experience = next(d for d in drawers if d['key'] == 'experience')
    child = next(c for c in experience['children'] if c['key'] == 'ease-of-use')
    child.update(requirement=INITIAL,
        acceptance_criteria='Initial untested assumption: reminders go out at 72 and 24 hours and replies are recorded as confirmations.',
        rationale='Synthetic starting assumption: reminders with confirmation will reduce missed appointments. This must be challenged.',
        goal_ids=['G-appointment-access'])
    sponsor.command('intake-drawers', dict(expected=intake_ref(), drawers=drawers))

    def publish_intent(design_focus, rationale):
        prepared = sponsor.command('intake-preflight', dict(expected=intake_ref(),
            research_focus=context['research_question'], design_focus=design_focus,
            open_questions=context['open_questions']))
        packet = latest(prepared['id'])['body']['packet']
        review = sponsor.command('intake-request', dict(expected=intake_ref(),
            preflight=ref(prepared['id']), confirm=True))
        for actor in ('sam', 'lee'):
            work[actor].command('intake-review', dict(expected=ref(review['id']),
                disposition='ready-for-investigation',
                rationale='Synthetic direction review: investigate this direction; publication does not validate it.'))
        sponsor.command('intake-publish', dict(expected=ref(review['id']), confirm=True, rationale=rationale))
        return packet

    sponsor_packet = publish_intent('Explore AI reminder and confirmation concepts, then respond to Research.',
        'Synthetic sponsor decision: publish a bounded starting direction and proposed requirement for investigation only.')
    intent_v1 = ref('INT-001')
    requirements = work['alex'].latest_records('requirement')
    initial = next(r for r in requirements if r['body']['text'] == INITIAL)
    requirement = asdict(initial['ref'])

    def publish(actor, title, source_text, observation, interpretation, recommendation,
                limitation, relation, inputs=None, previous=None, extra_sources=None, source_title=None):
        w = work[actor]
        source = w.command('domain-source', dict(title=source_title or title+' · synthetic source',
                                                 text=NOTICE+'\n\n'+source_text))
        saved = w.command('domain-save', dict(
            **({'expected': ref(previous['draft'])} if previous else {}),
            title=title, deliverable_type=w.domains.profile()['config']['deliverable_types'][0],
            observation=observation, source='Synthetic scenario notes; not collected patient evidence.',
            interpretation=interpretation, recommendation=recommendation, limitation=limitation,
            source_refs=[*(extra_sources or []), source['ref']], input_refs=inputs or [],
            links=[dict(ref=asdict(store.latest(requirement['id'], {SCOPE})['ref']), relation=relation, rationale=interpretation)]))
        complete_design_brief(w, latest(saved['id']))
        prepared = w.command('domain-prepare', dict(expected=ref(saved['id']),
            recipient='design' if actor == 'sam' else 'research',
            intent_implications='Keep clinician time in use; the cause of missed appointments and the right remedy are under investigation.',
            downstream_needs=recommendation, open_questions=limitation))
        result = w.command('domain-publish', dict(expected=ref(saved['id']),
            preflight=ref(prepared['domainHandoff']), confirm=True, release_sources=True))
        return dict(draft=saved['id'], source=source['ref'], contribution=ref(result['id']),
                    prepared_packet=latest(prepared['domainHandoff'])['body']['packet'], packet=result['packet'])

    # 2. Research maps the current journey and publishes a finding that challenges the intent.
    research = publish('sam', 'Research · Patients who miss appointments usually knew in advance (synthetic)',
        'Synthetic interviews with 12 patients and 4 front-desk staff, plus a review of 300 synthetic call-log entries. '
        '9 of 12 patients who had missed an appointment knew at least a day ahead that they could not attend. '
        'They did not reschedule because changing required a phone call during office hours, with holds averaging 11 minutes. '
        '2 of 12 said they forgot. Front-desk staff report that most late cancellations arrive too late to refill. '
        'Several patients said they would not want an AI to move a procedure or a first visit.\n\n'
        'Current-state user flow, mapped in FigJam (synthetic snapshot, not retrieved from Figma):\n'+FIGJAM_FLOW,
        'In this synthetic study, most missed appointments come from patients who could not easily reschedule, not from forgetting.',
        'The intent and requirement v1 target forgetting. Reminders with confirmation would not let these patients release their slot. The small synthetic sample does not establish prevalence.',
        'Reframe the problem around early, easy rescheduling and slot refill. Treat new-patient and procedure visits separately.',
        'All participants, counts and the FigJam flow are synthetic. No prevalence, clinical safety or financial benefit is established.',
        'challenges', source_title='Research · current rescheduling journey and interview notes · synthetic source')

    # 3. Research asks the sponsor to revise the intent; the sponsor decides and republishes.
    change = work['sam'].command('intent-refine', dict(source=research['contribution'], base_intent=intent_v1,
        field='business_challenge', proposed_value=CHALLENGE_V2,
        rationale='The published finding challenges the problem statement: rescheduling friction, not forgetting, drives most missed appointments.',
        requirement_refs=[requirement]))
    sponsor.command("intent-adopt", dict(expected=ref(change['id']), draft_expected=intake_ref(), response=CHALLENGE_V2,
        rationale='Synthetic sponsor decision: adopt the reframed problem and carry it into the next direction review.'))
    sponsor.command('intake-save', dict(expected=intake_ref(), step='value', **{**values, 'business_challenge': CHALLENGE_V2, 'need': NEED_V2, 'approach': APPROACH_V2,
        'pain_relievers': 'Let patients change an appointment any time without a phone call; free the slot early.',
        'gain_creators': 'Refill released time from the waitlist and show staff what changed.',
        'measures': values['measures']+' Added: released-slot refill rate.',
        'assumptions': 'Patients will reschedule early if it is easy; some visit types need staff. Design must test both.'}))
    # Keep the sponsor's framing answers in step with the revised fields, so every view shows version 2.
    sponsor.command('sponsor-save', dict(expected=intake_ref(), answers={'q6': dict(items=PAIN_V2.split('\n')),
        'q2': dict(items=[CHALLENGE_V2]), 'q9': dict(items=[APPROACH_V2]),
        'q21': dict(items=['Patients will reschedule early if it is easy; some visit types need staff. Design must test both.'])},
        framing=revised_framing(intake.draft(), CHALLENGE_V2, APPROACH_V2,
            'Patients will reschedule early if it is easy; some visit types need staff. Design must test both.')))
    sponsor.command('intake-accept-value', dict(expected=intake_ref(), confirm=True,
        rationale='Synthetic sponsor review of the revised value hypothesis after Research.'))
    sponsor.command('goals-save', dict(expected=intake_ref(), goals=[{**goal, 'review_basis': True}], measures=[*({**m, 'review_basis': True} for m in measures), dict(
        id='M-refill-rate', name='Released-slot refill rate',
        definition='Released appointment slots booked by another patient before their start time, divided by released slots.',
        population='Slots released through the assistant in the synthetic pilot.',
        data_source='Proposed scheduling-system and waitlist records; not implemented.',
        owner='Dana Okafor · synthetic measurement owner', guardrail='Do not offer slots the scheduling system has not confirmed as open.',
        review_plan='Agree a baseline with clinic managers before a real pilot.',
        goal_ids=['G-appointment-access'], active=True, basis_fields=['measures'])]))
    sponsor.command('intake-build', dict(expected=intake_ref(), confirm=True))
    revised_packet = publish_intent('Explore assistant concepts for early rescheduling and slot refill.',
        'Synthetic sponsor decision: revise the business intent. The goal is unchanged; the problem and approach now reflect Research.')
    intent_v2 = ref('INT-001')

    # 4. Design generates assistant concepts in Figma and publishes an evaluation.
    design1 = publish('lee', 'Design · Three AI assistant concepts, prototype v0.1 (synthetic)',
        'Synthetic prototype comparison, created in Figma (not retrieved). A: reminder bot with confirm and cancel. '
        'B: conversational rescheduling agent that offers open slots. C: self-serve reschedule page with an AI waitlist that refills released slots. '
        'In 8 synthetic sessions, participants preferred B and C. Every participant expected to move any visit, including first visits and procedures.',
        'Concepts B and C let patients release a slot early; concept A only records confirmations.',
        'B and C address the revised intent. All three assume any visit can be moved without staff, which clinic rules may not allow.',
        'Confirm which visit types the assistant may change, and design the staff handoff before choosing a concept.',
        'Synthetic sessions only. No usability, accessibility or scheduling-system evaluation has been performed.',
        'refines', inputs=[research['contribution']])
    issue = work['lee'].command('bridge-raise', dict(
        title='Which visits can the assistant move without staff? (synthetic)',
        question='Can the assistant reschedule every visit type, or must some go to staff, and how does the patient experience that handoff?',
        consequence='Self-serve rescheduling for restricted visits could book patients into slots without the required preparation or referral; blocking them silently would strand the patient.',
        kind='dependency', boards=['research-design'], owner='lee', route='requirement',
        target=requirement, requirement_refs=[requirement], packet_refs=[research['packet'], design1['packet']]))

    def respond(actor, note, action='comment', **extra):
        return work[actor].command('bridge-respond', dict(expected=ref(issue['id']), action=action, note=note, **extra))

    respond('sam', 'Synthetic Research: front-desk staff say new-patient visits need intake forms and referrals, and procedures need preparation instructions. Patients also told us they would not trust an AI to move those.')
    respond('lee', 'Synthetic Design: then concepts B and C need a handoff state: the assistant collects the reason and preferred times and tells the patient when staff will reply.')
    respond('lee', 'Design needs the actual visit-type rules before choosing a concept.',
        action='request-evidence', next_owner='sam',
        next_question='Which visit types need staff to change them, and what must a handoff capture so the patient is not stranded?')
    respond('sam', 'Synthetic Research answer: new-patient and procedure visits need staff (intake forms, referrals, preparation). '
        'A handoff should capture the reason, preferred times and how the patient wants to be contacted, and say when staff will reply.',
        action='answer-request')
    design2 = publish('lee', 'Design · Assistant with staff handoff, prototype v0.2 (synthetic)',
        'Synthetic prototype v0.2 combining B and C: reminder → change request → visit-type check → eligible: offer open slots → stored confirmation → released slot offered to waitlist; '
        'restricted: collect reason and preferred times → handoff to staff queue → patient told the expected reply time. '
        'A failed change keeps the original appointment. The v0.1 source is retained beside this revision.',
        'The revised flow separates self-service for eligible visits from a staff handoff for restricted ones.',
        'This reconciles Research\'s trust and preparation findings with Design\'s self-service concept without claiming either is validated.',
        'Adopt self-service rescheduling with a staff handoff for restricted visit types, for bounded design and testing.',
        'Synthetic flow only; no usability, reliability or scheduling-system evaluation. Clinic managers must validate the visit-type rules.',
        'refines', inputs=[research['contribution']], previous=design1, extra_sources=[design1['source']])
    respond('lee', 'Synthetic Design: prototype v0.2 adds the visit-type check, staff handoff and stored-only confirmation. The packet contains both v0.1 and v0.2. No usability test has occurred.')
    work['lee'].command('bridge-refresh', dict(expected=ref(issue['id']),
        packet_refs=[research['packet'], design2['packet']], requirement_refs=[requirement], target=requirement,
        note='Synthetic Research and Design reviewed the revised Design packet. Use v0.2 for the proposal; keep v0.1 and the earlier discussion in history.'))

    # 5. The requirement owner proposes, both domains review, and the owner decides.
    work['alex'].command('bridge-propose', dict(expected_issue=ref(issue['id']), text=REVISED,
        rationale='Serve the revised intent: early self-service changes for eligible visits, a staff handoff for restricted ones, and waitlist refill. Empirical validation remains open.',
        acceptance_criteria=CRITERIA, conditions=BOUNDARY+' Visit-type rules need clinic-manager validation before any real pilot.',
        selected=[research['contribution'], design2['contribution']], changes_intent=False))
    case_id = latest(issue['id'])['body']['linked']['ref']['id']
    for actor, disposition, rationale in [
        ('sam', 'supported-with-limits', 'Synthetic Research review: the wording addresses the rescheduling barrier and the trust concern. The synthetic sessions are not evidence; run real research before generalizing.'),
        ('lee', 'cleared-with-conditions', 'Synthetic Design review: prototype v0.2 expresses the proposed states. Test the handoff, stored-only confirmation and waitlist offer before implementation approval.')]:
        work[actor].command('review', dict(expected=ref(case_id), disposition=disposition, rationale=rationale))
    respond('priya', 'Synthetic sponsor position: this serves the revised intent. Track missed-appointment rate with refill rate as the new measure. Baselines, targets and financial benefit are still to be confirmed.')
    work['alex'].command('decision', dict(expected=ref(case_id), disposition='approve', confirm=True,
        rationale='Synthetic requirement-owner decision: approve requirement v2 for the bounded prototype. Self-service for eligible visits, staff handoff for restricted ones, stored-only confirmation and waitlist refill. This does not approve a real policy, deployment or clinical rule.'))
    resolved = latest(issue['id'])['body']['resolution']
    result = dict(project_id=PROJECT_ID, title=TITLE, fictional=True, evaluation='not-run',
        notice=NOTICE, issue=ref(issue['id']), requirement_before=requirement,
        requirement_after=resolved['requirement'], review=ref(case_id), decision=resolved['decision'],
        intent_before=intent_v1, intent_after=intent_v2, intent_refinement=ref(change['id']),
        packets=dict(sponsor_prepared=sponsor_packet, sponsor_revised_prepared=revised_packet,
            sponsor_published=latest('INT-001')['body'].get('packet') or dict(id='PKT-INTENT', revision=1),
            research_prepared=research['prepared_packet'], research=research['packet'],
            design_initial_prepared=design1['prepared_packet'], design_initial=design1['packet'],
            design_revised_prepared=design2['prepared_packet'], design_revised=design2['packet'], result=resolved['packet']))
    marker = store.put(MARKER_ID, 'demo-scenario', SCOPE, result)
    for raw in (result['issue'], result['requirement_before'], result['requirement_after'], result['review'],
                result['decision'], result['intent_before'], result['intent_after']):
        store.depend(marker, Ref(**raw), {SCOPE})
    return result


def seed_project(anchor):
    projects = Projects(anchor)
    with projects.db() as db:
        existing = db.execute('SELECT * FROM projects WHERE id=?', (PROJECT_ID,)).fetchone()
    if existing:
        with projects.locked(PROJECT_ID) as project:
            with closing(Store(project['path'])) as store:
                marker = store.latest(MARKER_ID, {SCOPE})
                if not marker:
                    raise ValueError('The demo project was changed or reset; it will not be overwritten.')
                return marker['body']
    path = projects.new_path()
    try:
        with closing(Store(path)) as store:
            with store.transaction():
                result = populate(store)
        with projects.db() as db:
            db.execute('INSERT INTO projects VALUES (?,?,?,?)', (PROJECT_ID, str(path), 1, now()))
    except Exception:
        # Only this newly allocated, unregistered demo file belongs to this attempt.
        path.unlink(missing_ok=True)
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True, type=Path, help='Existing local Workbench anchor database')
    args = parser.parse_args()
    if not args.db.is_file():
        parser.error('Choose an existing local Workbench database; other projects will be preserved.')
    print(json.dumps(seed_project(args.db), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
