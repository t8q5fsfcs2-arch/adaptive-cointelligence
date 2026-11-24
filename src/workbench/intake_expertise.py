"""Question-specific AI partner contracts shared by the UI and model context.

Adapted from the earlier workbench's expert-profile pattern, independently of
its application/data. Templates are scaffolds, never facts about an initiative.
"""
from copy import deepcopy

VERSION = '3'

def profile(short, question, hint, shape, starter, role, checks, connections):
    return dict(short_label=short, question=question, hint=hint, answer_shape=shape,
                starter=starter, expert_role=role, quality_checks=checks,
                connections=connections, answer_goal=hint, version=VERSION)

PROFILES = {
 'business_challenge': profile('Business Challenge', 'What problem or opportunity is driving this?',
    'Describe the problem or opportunity, who it affects, and why it matters. Use a concrete example.',
    ['Current situation', 'Where it breaks down', 'Human or business consequence'],
    'Today, [people] experience [problem] when [situation]. This leads to [consequence]. We know / still need to check [basis].',
    'Problem-framing AI partner', ['Separate the current problem from a proposed solution.', 'Distinguish observed experience from assumed scale or causality.'], ['beneficiaries','need','value','evidence']),
 'why_now': profile('Priority now', 'What makes this a priority now?',
    'Explain why this deserves attention ahead of other work, and what happens if it waits.',
    ['Reason to prioritize', 'Consequence of waiting'],
    'This deserves attention now because [growing problem, strategic priority, or opportunity]. If we wait, [consequence]. Any timing or deadline is [known / still to confirm].',
    'Prioritization AI partner', ['Look for changing costs or risks, strategic relevance, an opportunity window, or a real commitment.', 'A continuing costly problem can justify priority without a new event.', 'Distinguish urgency to investigate from urgency to implement.', 'Do not invent a deadline, trend, mandate or quantified loss.'], ['business_challenge','value','evidence']),
 'beneficiaries': profile('Primary users', 'Who should benefit most directly?',
    'Name the people doing the work or living with the problem, and the situation they share.',
    ['Specific people', 'Relevant situation', 'Benefit they need'],
    '[People in this situation] need [improvement]. They are the primary beneficiaries because [reason].',
    'Service-design AI partner', ['Separate primary beneficiaries from sponsors and supporting teams.', 'Avoid vague groups such as everyone or the business.'], ['jobs','need','supporting_users','value']),
 'supporting_users': profile('Supporting people', 'Who else is affected or helps deliver the value?',
    'Include the people who support, receive, or may be disadvantaged by changes to this work.',
    ['Supporting or affected role', 'Responsibility', 'Distinct need or impact'],
    '[Role] helps with [responsibility] and needs [support]. [Other group] may be affected by [impact].',
    'Stakeholder and service-design AI partner', ['Distinguish each role from the primary beneficiary.', 'Include burdens and missing perspectives as well as benefits.'], ['beneficiaries','jobs','assumptions']),
 'jobs': profile('User goals', 'What are these people trying to accomplish?',
    'Describe the result people need in a real situation, including how they want to feel.',
    ['When the need arises', 'What they need to accomplish', 'Why that matters'],
    'When [situation], [person] needs to [accomplish something] so they can [meaningful result].',
    'Jobs-to-be-done AI partner', ['Describe a goal that exists independently of a feature or product.', 'Explore confidence, control or social needs only when relevant.'], ['beneficiaries','need','gains']),
 'need': profile('Current difficulties', 'What makes that difficult today?',
    'Describe the obstacles, frustration or risk people experience while trying to achieve those goals.',
    ['Specific obstacle', 'When it occurs', 'Effect on the person'],
    'While trying to [goal], [person] encounters [obstacle], which causes [effect]. We have observed / suspect this because [basis].',
    'Problem and user-needs AI partner', ['Make the difficulty concrete without prescribing a feature.', 'Do not treat a request for a solution as evidence of the underlying need.'], ['jobs','beneficiaries','business_challenge','evidence']),
 'gains': profile('Desired improvements', 'What would a better experience enable?',
    'Describe what people could accomplish or feel if their situation improved.',
    ['Better outcome for the person', 'Why they would value it'],
    '[Person] could [better result] with [desired experience], which matters because [reason].',
    'User-outcomes AI partner', ['Separate benefits for people from business targets.', 'Avoid listing capabilities as if they were outcomes.'], ['beneficiaries','jobs','need','value']),
 'approach': profile('Possible approach', 'What approach might create that value?',
    'Describe your current idea and why it might help, leaving room for a better alternative.',
    ['Possible approach', 'Why it might help', 'What remains untested'],
    'We could [approach] to help [people] achieve [outcome]. This assumes [belief]; an alternative worth considering is [alternative / not yet explored].',
    'Solution-hypothesis AI partner', ['Treat the approach as an option to test, not an approved design.', 'Do not invent channels, features or delivery commitments.'], ['jobs','need','gains','value']),
 'job_support': profile('Supporting user goals', 'How would this approach help people achieve their goals?',
    'Connect a part of your proposed approach to a specific goal you already described.',
    ['User goal', 'Proposed support', 'Why it could help'],
    'To help [person] [stated goal], we propose [support]. It could help because [mechanism], which we still need to test.',
    'Value-fit AI partner', ['Use the actual stated jobs; surface any missing connection.', 'Keep proposed support distinct from proven performance.'], ['jobs','approach','value']),
 'pain_relievers': profile('Reducing difficulties', 'How would this approach reduce the difficulties?',
    'Explain which stated obstacle could improve and how the proposed approach would change it.',
    ['Existing difficulty', 'Proposed response', 'Expected effect'],
    '[Proposed response] could reduce [stated difficulty] by [mechanism]. We need to test [uncertainty].',
    'Service-improvement AI partner', ['Trace every response to an actual stated pain.', 'Surface burdens shifted to another person or team.'], ['need','approach','supporting_users','value']),
 'gain_creators': profile('Creating improvements', 'How would this approach create the improvements people want?',
    'Connect the proposed approach to a benefit people would notice or value.',
    ['Desired improvement', 'How the approach could enable it', 'Assumption to test'],
    '[Approach] could help [person] achieve [stated improvement] by [mechanism]. This depends on [assumption].',
    'Outcome and value-fit AI partner', ['Use the stated gains rather than generic promises.', 'Distinguish intended benefit from validated effect.'], ['gains','approach','value']),
 'value': profile('Value proposition', 'What value does this initiative offer?',
    'Connect who benefits, what improves, how the approach might help, and why it matters.',
    ['Beneficiary and need', 'Proposed value mechanism', 'Business reason', 'Key uncertainty'],
    'For [people] who [need], [approach] could [benefit] by [mechanism]. This matters because [business reason], subject to [key assumption].',
    'Business-case AI partner', ['Synthesize the supplied answers without inventing missing facts.', 'Preserve human edits and distinguish intended value from a promise.'], ['business_challenge','beneficiaries','jobs','need','gains','approach','why_now','measures']),
 'measures': profile('Success metrics', 'What measurable changes would demonstrate the promised value?',
    'Define one metric for each important benefit: what changes, for whom, and by how much. Include a baseline and target if known.',
    ['Benefit to demonstrate', 'Metric and population', 'Baseline → target'],
    'For [people / process], improve [measure] from [baseline] to [target], demonstrating [benefit]. If a number is unknown, say so. Illustrative example only: reduce average handoff time from 20 to 10 minutes to help coordinators respond sooner.',
    'Outcome measurement AI partner', [
        '“Faster resolution” is an outcome. A metric specifies what you will count or time, whose experience it covers, and what improvement would count.',
        'Link each metric directly to a benefit in the current value proposition or a stated business outcome. Explain the connection.',
        'Define the measure precisely: unit, population or process, direction of change, and denominator for a rate. Preserve known baselines and targets; flag unknowns.',
        'Do not change the outcome while defining it: repeated entry is entering the same information again, not all data entry. Proposed definitions do not establish available telemetry.',
        'Favor two to four meaningful metrics over a generic KPI inventory. Operational performance, experience, quality, adoption and decision readiness are possibilities only when they fit the promised value.',
        'A proposed metric is not an established KPI. Never invent baselines, numeric targets, ROI, dates or committed owners.',
        'Distinguish research evidence about the problem from performance after a solution exists. Usage or submission volume alone does not prove value; consider a material harm or tradeoff.',
        'Review timing, data sources and accountable measurement roles belong in the connected review plan. Do not prescribe a technical implementation.'
    ], ['value','business_challenge','beneficiaries','gains','desired_outputs','measure_review','evidence']),
 'measure_review': profile('Review plan', 'When and how will we check the metrics?',
    'For each metric, name the data source, who will review it, and when. A first check could be 30, 60 or 90 days after launch; leave unconfirmed details open.',
    ['Metric', 'Data source and reviewer', 'First review and cadence'],
    'For [metric], use [data source] and have [role, if agreed] review it [time after launch / milestone / date]. Repeat [cadence, if needed]. Still to confirm: [baseline, access or ownership]. Different metrics may need different review points.',
    'Measurement planning AI partner', [
        'Give each metric a realistic review point: when enough information should exist to judge whether the intended benefit is happening.',
        'Connect the review plan to the actual success metrics and value proposition. Flag missing data sources, baseline collection or unconfirmed ownership.',
        'Distinguish first review from ongoing monitoring, and problem-discovery research from evaluation after launch. Do not invent a launch date or a commitment.',
        'Suggest a concise plan as a proposal; never claim a data source exists, a reviewer has agreed, or monitoring is active without supplied support.'
    ], ['measures','value','evidence','sources','dependencies']),
 'evidence': profile('Available evidence', 'What supports the case so far?',
    'Explain what your notes, experience or data actually tell you and what they leave unanswered.',
    ['What the evidence supports', 'What it does not establish', 'Why the gap matters'],
    '[Source or experience] suggests [specific observation]. It does not yet establish [scale, cause or outcome]. That matters because [decision affected].',
    'Evidence and inference AI partner', ['Analyze the supported claim and inferential leap, not revision history or governance labels.', 'Do not demand new research before research has begun.', 'Respect source limitations and distinguish sponsor experience from participant findings.'], ['business_challenge','value','assumptions','measures']),
 'assumptions': profile('Assumptions to test', 'What are we relying on that may not be true?',
    'Name a belief that could change the case if it turns out to be wrong.',
    ['Belief', 'Consequence if wrong', 'What could change our view'],
    'We assume [belief]. If wrong, [effect on the case]. We could investigate it through [evidence or question].',
    'Assumption-testing AI partner', ['Prioritize the most consequential uncertainty.', 'Include beliefs about the problem and the proposed response, without pretending they are validated.'], ['value','approach','evidence','measures']),
 'assumption_owner': profile('Investigation owner', 'Who will coordinate investigating these assumptions?',
    'Choose someone who can organize the investigation and bring unresolved decisions to the right people.',
    ['Accountable coordinator', 'Access or support they need'],
    'Choose the coordinator for learning, not necessarily the person who approves a solution.',
    'Accountability AI partner', ['Explain coordination versus decision authority.', 'Only the human may assign an owner; never infer acceptance or make an assignment.'], ['assumptions','evidence']),
 'user_situation': profile('Real work situations', 'When and where does this need arise?',
    'Describe a real work moment: what triggers it, what people use, and who they depend on.',
    ['Trigger and setting', 'Current steps and tools', 'Handoff or exception'],
    'When [trigger], [person] currently [work] using [tools or information]. They depend on [other role]; it becomes difficult when [exception].',
    'Workflow and service-blueprint AI partner', ['Follow actors and needs already established in the value proposition.', 'Describe current experience separately from a future concept.'], ['value','beneficiaries','jobs','need']),
 'work_kind': profile('Initiative type', 'What kind of initiative is this?',
    'Choose the closest fit so the requirement drawers use a useful starting structure.',
    ['Main kind of change', 'Mixed or uncertain scope'],
    'Digital: a product or system. Operational: how work is done. Market: a new offer or venture. Other: an inquiry that does not yet fit.',
    'Initiative-framing AI partner', ['Explain the available categories using the supplied scope.', 'The selection is a starting structure, not a delivery commitment; the human chooses.'], ['value','approach','in_scope']),
 'in_scope': profile('Included work', 'What will this initiative include?',
    'Set the smallest useful boundary that can deliver or test the stated value.',
    ['People and work included', 'Starting boundary', 'Unsettled edge'],
    'We will focus on [people / work / situation] to [stated value]. The starting boundary is [limit]; [edge] still needs agreement.',
    'Scope and delivery AI partner', ['Tie included work to the value and user goals.', 'Distinguish a proposed boundary from an approved commitment.'], ['value','jobs','user_situation','out_scope']),
 'out_scope': profile('Excluded work', 'What will this initiative leave out?',
    'Name adjacent work someone might reasonably expect, and explain why it is excluded or deferred.',
    ['Excluded or deferred work', 'Reason', 'When to revisit if relevant'],
    '[Adjacent work] is outside this effort because [reason]. [Unresolved boundary] is still to be decided.',
    'Scope-boundary AI partner', ['Distinguish exclusions from unanswered scope questions.', 'Flag exclusions that make the proposed value impossible.'], ['value','in_scope','user_situation']),
 'constraints': profile('Rules and limits', 'What rules or limits must this work respect?',
    'Describe real policy, operational, access or resource limits, including who can confirm them.',
    ['Limit or rule', 'Effect on the work', 'Source or person who can confirm'],
    '[Rule or limit] means we must [effect]. It comes from [source / person], and [applicability] is confirmed / still to check.',
    'Governance and operational-constraints AI partner', ['Separate mandatory rules, preferences and assumptions.', 'Do not invent policy or silently resolve conflicting authorities.'], ['value','in_scope','sources','operations_question']),
 'sources': profile('Sources and guidance', 'What material or expertise should guide this work?',
    'Name relevant documents, data and people, and explain what each can clarify.',
    ['Source or expert', 'What it informs', 'Authority or access still to check'],
    '[Document, data or person] can clarify [question]. Its authority / applicability / availability is [known or to confirm].',
    'Knowledge and source-authority AI partner', ['Distinguish governing policy from background material and unassessed evidence.', 'Do not infer source authority, access or consent.'], ['evidence','constraints','value','open_questions']),
 'open_questions': profile('Unresolved questions', 'What still needs an answer before we can decide?',
    'Prioritize unknowns that could change the value, scope or next decision.',
    ['Question', 'Decision it affects', 'Who could help answer it'],
    'We need to understand [unknown] because it affects [decision]. [Role / person to identify] could help resolve it through [evidence or event].',
    'Decision and uncertainty AI partner', ['Separate investigation responsibility from approval authority.', 'Keep unknowns explicit; do not manufacture closure.'], ['value','assumptions','in_scope','constraints']),
 'research_question': profile('Research inquiry', 'What should Research help us understand?',
    'Ask a neutral question about people, their current needs or the assumptions behind the value.',
    ['Uncertainty to investigate', 'People or situation', 'Decision informed'],
    'How / when / why do [people] experience [situation], and what would this tell us about [assumption or decision]?',
    'Research-design AI partner', ['Avoid leading questions that seek approval for a preferred solution.', 'Separate learning about the existing problem from testing a concept.', 'Use the value and assumptions to focus inquiry, not to predetermine findings.'], ['value','assumptions','user_situation','measures']),
 'operations_question': profile('Operational inquiry', 'What should Operations help us understand?',
    'Ask what would make the proposed value workable in day-to-day delivery.',
    ['Operational uncertainty', 'Handoff, dependency or exception', 'Decision informed'],
    'What would [team] need to [deliver the proposed value], especially when [handoff or exception]? This would clarify [feasibility decision].',
    'Service-operations AI partner', ['Connect feasibility questions to the stated value and real work.', 'Consider capacity, recovery, ownership and dependencies without assuming a design is approved.'], ['value','approach','supporting_users','constraints','user_situation'])
}

# Intake sections are navigation, not approval gates.
PROFILES['strategic_relevance'] = profile(*('Strategic relevance', 'Which business objective does this support?', 'Name the objective and explain how the proposed benefit contributes to it.', ['Named objective', 'Contribution', 'Basis or uncertainty'], 'This supports [objective] by [contribution]. The connection is [supported by / still to confirm].', 'Business strategy AI partner', ['Do not invent a corporate strategy or sponsor commitment.', 'Explain the causal link, not just a strategic label.'], ['business_challenge', 'value', 'why_now', 'measures']))
PROFILES['user_actions'] = profile(*('Current actions', 'What do people do today?', 'Describe the main steps people take from the trigger to completion.', ['Actor and action', 'Sequence', 'Completion'], 'After [trigger], [role] does [action], then [next action], until [result].', 'User journey AI partner', ['Describe current behavior separately from a future design.', 'Use concrete verbs and identify the actor at each step.'], ['beneficiaries', 'jobs', 'user_situation', 'desired_outputs']))
PROFILES['bottlenecks'] = profile(*('Bottlenecks', 'Where does the current flow break down?', 'Locate waiting, repeated work, obstacles or failures in the current steps.', ['Step affected', 'Obstacle', 'Consequence'], 'At [step], [obstacle] causes [delay, rework or failure]. This is [observed / to investigate].', 'Workflow diagnosis AI partner', ['Locate the obstacle in the flow.', 'Do not infer prevalence or root cause without evidence.'], ['user_actions', 'need', 'evidence']))
PROFILES['tools'] = profile(*('Tools and information', 'What do people use to do this work?', 'Name the tools, documents or information needed at each important step.', ['Tool or information', 'Step supported', 'Access or quality issue'], '[Role] uses [tool or information] for [step]. [Gap] remains to confirm.', 'Service design AI partner', ['Distinguish current tools from proposed technology.', 'Do not assume access or integration exists.'], ['user_actions', 'constraints', 'sources']))
PROFILES['handoffs'] = profile(*('Handoffs', 'Where does work pass between people or systems?', 'Describe who sends what to whom, and what the receiver needs to continue.', ['Sender and receiver', 'Information or work transferred', 'Failure or exception'], '[Sender] passes [work / information] to [receiver] when [event]. The receiver needs [input].', 'Service blueprint AI partner', ['Identify missing information and responsibility at the handoff.', 'Keep proposed future handoffs distinct from the current flow.'], ['supporting_users', 'user_actions', 'tools', 'bottlenecks']))
PROFILES['desired_outputs'] = profile(*('Desired outputs', 'What should people have when the work is done?', 'Describe the usable result and how the person recognizes completion.', ['Result', 'Recipient', 'Completion condition'], '[Person] needs [usable result] to [goal]. The work is complete when [condition].', 'User outcomes AI partner', ['Separate a usable output from the longer-term benefit.', 'Connect the output to a stated job.'], ['jobs', 'gains', 'user_actions', 'measures']))
PROFILES['dependencies'] = profile(*('Dependencies', 'What other work or decisions does this depend on?', 'Name what must be available, who can confirm it, and the consequence if it is missing.', ['Dependency', 'Owner or source to confirm', 'Effect if missing'], 'This depends on [input / decision / work]. [Role, if known] can confirm it; without it [effect].', 'Dependency analysis AI partner', ['Do not assume an owner has committed.', 'Distinguish a dependency from a general risk.'], ['value', 'in_scope', 'constraints', 'handoffs']))
PROFILES['value'].update(hint='Connect the primary beneficiary and their key jobs, pains and gains to the offering, pain relief and gain creation.', answer_goal='Produce a concise value-fit statement, not a full business case.', connections=['beneficiaries','jobs','need','gains','approach','job_support','pain_relievers','gain_creators'], quality_checks=['Prioritize the needs that matter most to the beneficiary.', 'Show how the offering addresses those needs without claiming proven fit.', 'Keep urgency, workflow details, scope and KPIs in their own sections.'])
PROFILES['user_situation'].update(short_label='Triggers and setting', hint='Describe the event that starts this work, where it happens, and any conditions that matter.', connections=['beneficiaries','jobs','user_actions','need'])


def expert_context(field, values, skill, profiles=None):
    """Snapshot exact connected answers; do not infer a metric or benefit here."""
    profiles = profiles or PROFILES
    key = field if skill == 'coach-field' else 'value'
    selected = deepcopy(profiles[key])
    return {'expertise_version': VERSION, 'expert_profile': {'field': key, **selected},
            'connected_answers': [dict(field=k, text=values.get(k, '')) for k in selected['connections']],
            'question_profiles': deepcopy(profiles) if skill in ('seed-value','context-questions','review-value') else {key: selected}}
