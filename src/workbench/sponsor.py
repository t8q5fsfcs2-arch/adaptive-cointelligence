"""Sponsor flow over the existing private intake and governed publications."""
from copy import deepcopy
from dataclasses import asdict
import json
import hashlib
from pathlib import Path
from .core import Ref, StaleBasis
from .decisions import SCOPE, now
from .intake import PRIVATE, ALL_FIELDS
from .validation import optional, reference

QUESTIONS = json.loads((Path(__file__).parent/'config/sponsor_questions.json').read_text())
FIELDS = {'q2':'business_problems','q3':'desired_outcomes','q4':'user_roles','q5':'current_process','q6':'pain_points','q7':'formal_evidence','q8':'informal_evidence','q9':'future_process','q10':'must_haves','q11':'uncertain_scenarios','q12':'fallbacks','q13':'edge_cases','q14':'in_scope','q15':'out_scope','q16':'scope_unknowns','q17':'measures','q18':'measure_review','q19':'operating_limits','q20':'project_limits','q21':'project_risks','q22':'dependencies','q23':'stakeholders'}
LEGACY = {'q2':'business_challenge','q3':'desired_outputs','q4':'beneficiaries','q5':'user_actions','q6':'bottlenecks','q7':'evidence','q9':'approach','q16':'open_questions','q19':'constraints','q21':'assumptions','q23':'supporting_users'}
COACH = {q:LEGACY.get(q,FIELDS[q]) for q in FIELDS}
COACH.update(q8='evidence',q10='in_scope',q11='open_questions',q12='constraints',q13='open_questions',q20='constraints',q21='assumptions')
# Only these legacy fields are direct bindings. Combined evidence/constraints,
# structured roles and separate risks/assumptions cannot be inverted safely.
DIRECT_LEGACY = {q: LEGACY[q] for q in ('q2', 'q3', 'q5', 'q6', 'q9', 'q16')}
FIELD_QUESTIONS = {field: q for q, field in FIELDS.items() if q != 'q4'}
FIELD_QUESTIONS.update({field: q for q, field in DIRECT_LEGACY.items()})

def answer(text='', roles=None):
    return dict(items=[x for x in text.split('\n') if x.strip()], roles=roles or [], confirmed=False, completed=False, ai=False, edited=False, handled=bool(text))

def answer_text(a):
    if a.get('roles'):
        return '\n\n'.join('\n'.join([r['name'],*['%s: %s'%(k,r[k]) for k in ('does','needs','where','often') if r[k]]]) for r in a['roles'])
    return '\n'.join(a['items'])

def sync_intent_field(body, field, text, *, restored_answer=None):
    """Keep exact question bindings coherent when a native intent field changes.

    This edits the private draft only. Revised wording never inherits completion,
    confirmation or model provenance. Disposal may restore an exact published
    answer when its wording matches the restored value; history is never edited.
    """
    values = body['values']
    left_for_review = _sync_framing_mirrors(body, field, values.get(field, ''), text)
    updates = {field: text}
    q = FIELD_QUESTIONS.get(field)
    if q:
        updates[FIELDS[q]] = text
        if q in DIRECT_LEGACY:
            updates[DIRECT_LEGACY[q]] = text
        answers = body.setdefault('sponsor_brief', {}).setdefault('answers', {})
        current = answers.get(q)
        if restored_answer is not None and answer_text(restored_answer) == text:
            answers[q] = deepcopy(restored_answer)
        elif current is None or answer_text(current) != text:
            # A narrative may contain more than 40 lines; keep it as one editable
            # item so the next ordinary question save retains its exact wording.
            answers[q] = {**answer(text), 'items': [text] if text else [], 'edited': True}
        if current != answers[q] and q in body.get('sponsor_question_provenance', {}):
            body['sponsor_question_provenance'][q]['status'] = 'sponsor-edited-after-coaching'
    for key, value in updates.items():
        if values.get(key, '') != value and key in body.get('field_provenance', {}):
            body['field_provenance'][key]['status'] = 'sponsor-edited-after-coaching'
        values[key] = value
    return left_for_review

# Framing wording that mirrors an intent field. The statement and context are the same text by
# design and always move together; summary lines move when they still match the earlier wording,
# otherwise they are left as the sponsor wrote them and reported for review.
FRAMING_MIRRORS = {'business_challenge': ('statement', 'summary.problem'), 'user_situation': ('context',), 'approach': ('summary.solution',)}
FRAMING_LABELS = {'summary.problem': 'Summary · problem', 'summary.solution': 'Summary · offering'}

def _sync_framing_mirrors(body, field, old, text):
    framing = body.get('sponsor_brief', {}).get('framing')
    left = []
    if not isinstance(framing, dict):
        return left
    for path in FRAMING_MIRRORS.get(field, ()):
        if '.' in path:
            group, key = path.split('.')
            summary = framing.setdefault(group, {})
            current = summary.get(key, '')
            if current.strip() in ('', old.strip()):
                summary[key] = text
                body['values']['executive_summary'] = json.dumps(summary, ensure_ascii=False)
            elif current.strip() != text.strip():
                left.append(FRAMING_LABELS.get(path, path))
        else:
            framing[path] = text
    return left

def framing_responses(f, v):
    return {'name':f['name'], 'context':f['context'], 'statement':f['statement'],
            **{'summary-'+k:f['summary'].get(k,'') for k in ('problem','solution','risk','options')},
            **{'fit-'+k:v.get(k,'') for k in ('value','gains','why_now')}}

def response_digest(text):
    return hashlib.sha256(text.strip().encode()).hexdigest()

class Sponsor:
    def __init__(self,w):self.w=w;self.store=w.store;self.intake=w.intake
    def state(self):
        if self.w.actor!='priya' or not self.intake.latest('INTAKE-001'):return None
        d=self.intake.draft();v=d['body']['values'];saved=deepcopy(d['body'].get('sponsor_brief',{}));answers=saved.setdefault('answers',{})
        for q,k in FIELDS.items():
            if q not in answers:
                text=v.get(k) or v.get(LEGACY.get(q,''),'') or ''
                answers[q]=answer(text, [dict(name=text,does='',needs='',where='',often='')] if q=='q4' and text else None)
                if q=='q4':answers[q]['items']=[]
            answers[q].setdefault('completed',False)
        saved.setdefault('framing',dict(name=d['body']['title'],context=v.get('user_situation',''),statement=v.get('business_challenge',''),summary=dict(problem=v.get('business_challenge',''),solution=v.get('approach',''),risk=v.get('project_risks') or v.get('assumptions',''),options='')))
        saved['framing']['name']=d['body']['title']
        saved['framing_completed']={k:bool(text.strip() and saved.get('framing_completion',{}).get(k)==response_digest(text)) for k,text in framing_responses(saved['framing'],v).items()}
        return dict(ref=asdict(d['ref']),questions=QUESTIONS,brief=saved,coach_fields=COACH,imported='sponsor_brief' not in d['body'])
    def save(self,data):
        self.intake.sponsor()
        with self.store.transaction():
            d=self.intake.draft(data.get('expected'));b=d['body'];v=b['values'];previous_values=deepcopy(v);brief=self.state()['brief'];patch=data.get('answers',{})
            if not isinstance(patch,dict) or not set(patch)<=set(FIELDS):raise ValueError('Choose questions from this sponsor brief')
            for q,a in patch.items():
                if not isinstance(a,dict):raise ValueError('Supply a question response')
                items=a.get('items',[]);roles=a.get('roles',[])
                if not isinstance(items,list) or len(items)>40 or any(not isinstance(t,str) or len(t)>20000 for t in items):raise ValueError('Use at most 40 response items, each under 20,000 characters')
                if not isinstance(roles,list) or len(roles)>20 or (q!='q4' and roles):raise ValueError('Use user cards only for the users question')
                clean=[]
                for r in roles:
                    if not isinstance(r,dict):raise ValueError('Supply a user card')
                    clean.append({k:optional(r,k) for k in ('name','does','needs','where','often')})
                if q=='q4' and any(t.strip() for t in items):raise ValueError('Use structured cards for users')
                if type(a.get('confirmed',False)) is not bool:raise ValueError('Choose whether the response is confirmed')
                completion=a.get('completed')
                if 'completed' in a and type(completion) is not bool:raise ValueError('Choose whether the question is complete')
                a=dict(items=[t.strip() for t in items],roles=clean,confirmed=a.get('confirmed',False),ai=False,edited=True,handled=True)
                text=answer_text(a)
                if len(text)>20000:raise ValueError('Keep a complete response within 20,000 characters')
                if a['confirmed'] and not text.strip():raise ValueError('Add a response before confirming it')
                prior_answer=brief['answers'][q]
                a['completed']=completion if completion is not None else bool(prior_answer.get('completed',False) and text==answer_text(prior_answer))
                has_answer=any(r['name'].strip() for r in clean) if q=='q4' else bool(text.strip())
                if a['completed'] and not has_answer:raise ValueError('Add an answer before marking the question complete')
                if text!=answer_text(prior_answer) and q in b.get('sponsor_question_provenance',{}):
                    b['sponsor_question_provenance'][q]['status']='sponsor-edited-after-coaching'
                brief['answers'][q]=a;v[FIELDS[q]]=text
                if q in LEGACY and q not in ('q4','q6','q7','q19','q21','q23'):v[LEGACY[q]]=text
                if q=='q4':v['beneficiaries']='\n'.join(r['name'] for r in clean);v['user_situation']=text
                if q=='q6':v['bottlenecks']=text
                if q in ('q7','q8'):v['evidence']='\n\n'.join(label+':\n'+answer_text(brief['answers'][id]) for id,label in [('q7','Formal evidence'),('q8','Informal evidence')] if answer_text(brief['answers'][id]))
                if q in ('q19','q20'):v['constraints']='\n\n'.join(label+':\n'+answer_text(brief['answers'][id]) for id,label in [('q19','Operating conditions'),('q20','Project rules')] if answer_text(brief['answers'][id]))
            if 'framing' in data:
                f=data['framing']
                if not isinstance(f,dict):raise ValueError('Supply the project framing')
                framing={k:optional(f,k) for k in ('name','context','statement')}
                if not framing['name'] or len(framing['name'])>200:raise ValueError('Name the project in 200 characters or fewer')
                if not isinstance(f.get('summary',{}),dict):raise ValueError('Supply an executive summary object')
                framing['summary']={k:optional(f.get('summary',{}),k) for k in ('problem','solution','risk','options')}
                previous_framing=brief['framing']
                brief['framing']=framing;b['title']=framing['name']
                if framing['statement']!=previous_framing['statement']:v['business_challenge']=framing['statement']
                if framing['context']!=previous_framing['context']:v['user_situation']=framing['context']
                if framing['summary']!=previous_framing['summary']:v['executive_summary']=json.dumps(framing['summary'],ensure_ascii=False)
                project=self.store.latest('PROJECT-001',{SCOPE})
                if project['body']['title']!=framing['name']:self.store.put('PROJECT-001','project',SCOPE,{**project['body'],'title':framing['name']},project['ref'].revision)
            if 'fit' in data:
                fit=data['fit']
                allowed={'beneficiaries','jobs','need','gains','approach','job_support','pain_relievers','gain_creators','value','why_now','strategic_relevance','assumptions','assumption_owner','research_question','operations_question','investment_case'}
                if not isinstance(fit,dict) or not set(fit)<=allowed:raise ValueError('Choose a value-fit field')
                for k in fit:v[k]=optional(fit,k)
                if v.get('assumption_owner') not in ('priya','sam','lee','alex','maya'):raise ValueError('Choose an assumption owner')
            responses=framing_responses(brief['framing'],v)
            completions={k:digest for k,digest in brief.get('framing_completion',{}).items() if k in responses and responses[k].strip() and digest==response_digest(responses[k])}
            requested=data.get('framing_completed',{})
            if not isinstance(requested,dict) or not set(requested)<=set(responses):raise ValueError('Choose a Business Intent response')
            for key,complete in requested.items():
                if type(complete) is not bool:raise ValueError('Choose whether the response is complete')
                if complete:
                    if not responses[key].strip():raise ValueError('Add an answer before marking the response complete')
                    completions[key]=response_digest(responses[key])
                else:completions.pop(key,None)
            brief.pop('framing_completed',None)
            brief['framing_completion']=completions
            for key,value in v.items():
                if value!=previous_values.get(key) and key in b.get('field_provenance',{}):
                    b['field_provenance'][key]['status']='sponsor-edited-after-coaching'
            b['sponsor_brief']=brief
            ref=self.intake.save_draft(d,b)
            return dict(message='Sponsor draft saved.',ref=asdict(ref))
    def coach(self,data):
        self.intake.sponsor();q=data.get('question')
        if q not in FIELDS:raise ValueError('Choose a sponsor question')
        if data.get('consent') is not True:raise ValueError('Confirm sending this saved response to the configured AI partner')
        s=self.state();d=self.intake.draft(data.get('expected'));question=next(x for x in QUESTIONS if x['id']==q)
        message=optional(data,'message') or 'Evaluate the response, explain what matters and ask the next useful question.'
        return self.w.coaching.run(dict(expected=asdict(d['ref']),skill='coach-field',field=COACH[q],sources=[],consent=True,
            question_context=dict(id=q,prompt=question['prompt'],title=question['title']),message='Sponsor question: '+question['prompt']+'\nSaved answer: '+answer_text(s['brief']['answers'][q])+'\n'+message),working_answer=answer_text(s['brief']['answers'][q]))
    def apply_advice(self,data):
        self.intake.sponsor()
        if data.get('confirm') is not True:raise ValueError('Review the suggested response before applying it')
        q=data.get('question')
        if q not in FIELDS or q=='q4':raise ValueError('Edit structured user-role cards directly')
        with self.store.transaction():
            draft=self.intake.draft(data.get('expected'))
            run=self.store.latest(optional(data,'run_id'),{PRIVATE});b=run['body']
            if run['kind']!='intake-coach-run' or (b.get('question_context') or {}).get('id')!=q:raise ValueError('Choose advice for this exact question')
            if b['basis']!=asdict(draft['ref']):raise StaleBasis('The brief changed. Request current advice before applying it.')
            from .scope_context import require_coaching_basis
            require_coaching_basis(self.intake,draft,b)
            if b['configuration_fingerprint']!=self.w.coaching.settings.coaching()['fingerprint']:raise StaleBasis('AI partner settings changed. Request fresh advice.')
            for raw in b.get('sources',[]):
                if self.store.latest(raw['id'],{PRIVATE})['ref']!=reference(raw):raise StaleBasis('A source changed. Request current advice.')
            key='question:'+q
            if key in b['applied']:raise ValueError('This question suggestion was already used')
            suggestion=next((s for s in b['output']['suggestions'] if s['field']==COACH[q]),None)
            if not suggestion:raise ValueError('No wording was proposed for this question')
            wording=optional(data,'edited_text') if 'edited_text' in data else suggestion['text']
            if not wording:raise ValueError('Keep a nonempty proposed response')
            result=self.save(dict(expected=asdict(draft['ref']),answers={q:dict(items=wording.split('\n'),roles=[],confirmed=False)}))
            current=self.intake.draft();body=current['body'];body.setdefault('sponsor_question_provenance',{})[q]=dict(run=asdict(run['ref']),original_text=suggestion['text'],rationale=suggestion['rationale'],citations=suggestion.get('citations',[]),status='sponsor-edited-suggestion' if wording!=suggestion['text'] else 'sponsor-adopted-suggestion',at=now())
            self.intake.save_draft(current,body);b['applied'][key]=wording
            self.store.put(run['ref'].id,run['kind'],PRIVATE,b,run['ref'].revision)
            return dict(message='Suggested response saved as an editable, unconfirmed draft.')
    def apply_native_advice(self,data):
        """Preserve supported direct bindings when existing source drafting is used."""
        with self.store.transaction():
            result=self.w.coaching.apply(data);draft=self.intake.draft();b=draft['body'];brief=b.get('sponsor_brief')
            if not brief:return result
            field=data.get('field');bindings={'business_challenge':'q2','desired_outputs':'q3','user_actions':'q5','bottlenecks':'q6','in_scope':'q14','out_scope':'q15','measures':'q17','measure_review':'q18'}
            q=bindings.get(field)
            if q:
                brief['answers'][q]=answer(b['values'][field]);brief['answers'][q].update(ai=True,origin='Reviewed source suggestion')
                b['values'][FIELDS[q]]=b['values'][field]
            else:
                brief.setdefault('alignment_notes',{})[field]='Intake wording updated from a reviewed source suggestion; check related question responses and value fit.'
            self.intake.save_draft(draft,b)
            return result
