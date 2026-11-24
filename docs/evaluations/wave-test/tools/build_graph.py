"""Builds the block graph for each wave of the synthetic clinic project.
Each wave adds or revises records. Links are typed and pinned to revisions."""
import json, pathlib, copy
OUT = pathlib.Path(__file__).resolve().parent.parent / 'graph'

def L(rel, target, rev, conditions='', use=''):
    return {'relation': rel, 'target': target, 'target_rev': rev, 'conditions': conditions, 'use': use}

waves = {
1: [
 {'id':'GOAL-1','kind':'goal','group':'Sponsor','rev':1,'date':'2026-03-02','author':'Dana Ortiz','text':'Automated reminders cut missed visits from 18% to 10% within six months of launch.','basis':'sponsor assertion'},
 {'id':'HYP-1','kind':'hypothesis','group':'Sponsor','rev':1,'date':'2026-03-02','author':'Dana Ortiz','text':'Patients miss mainly because they forget; a 48-hour reminder fixes most of it.','evidence':'Low'},
 {'id':'FIND-1','kind':'finding','group':'Research','rev':1,'date':'2026-04-10','author':'Sam Patel','text':'Most people who missed a visit knew in advance (9 of 12); the barrier is rescheduling, not remembering.','evidence':'Moderate','applies_to':'shift and irregular-hours workers (all 12 recruited from evening-clinic list)','links':[L('challenges','HYP-1',1)]},
 {'id':'OBS-P07','kind':'observation','group':'Research','rev':1,'date':'2026-03-24','author':'Sam Patel','text':'"I knew on Tuesday I couldn\'t come. The office only answers nine to five."','applies_to':'warehouse shift worker','links':[L('supports','FIND-1',1)]},
 {'id':'FIND-2','kind':'finding','group':'Research','rev':1,'date':'2026-04-18','author':'Sam Patel','text':'7 of 12 interviewees tried to reschedule after 5 pm; call logs show an evening spike in abandoned calls.','evidence':'Moderate'},
],
2: [
 {'id':'OBS-BASE','kind':'observation','group':'Operations','rev':1,'date':'2026-04-22','author':'Priya Nair','text':'True missed-visit rate is 16%, not 18%.'},
 {'id':'DEC-1','kind':'decision','group':'Sponsor','rev':1,'date':'2026-05-06','decided_by':'Dana Ortiz','status':'approved','text':'Change GOAL-1 to rev 2.','links':[L('rests-on','FIND-1',1,use='rationale'),L('rests-on','OBS-BASE',1,use='rationale')]},
 {'id':'GOAL-1','kind':'goal','group':'Sponsor','rev':2,'date':'2026-05-06','author':'Dana Ortiz','text':'Cut missed visits from 16% to 11% within six months by letting patients reschedule themselves at any hour; reminders not the main lever.','changed_by':'DEC-1','links':[L('rests-on','DEC-1',1,use='rationale')]},
 {'id':'REQ-2','kind':'requirement','group':'Research','rev':1,'date':'2026-05-20','text':'Patients who know they cannot attend can reschedule without phoning.','evidence':'Moderate','links':[L('supported-by','FIND-1',1,conditions='shift and irregular-hours workers',use='evidence')]},
 {'id':'REQ-3','kind':'requirement','group':'Research','rev':1,'date':'2026-05-20','text':'Rescheduling works at any hour, 24/7, without staff.','evidence':'Moderate','interpretation':'Research reads "after 5 pm" as a need for round-the-clock self-service.','links':[L('supported-by','FIND-2',1,use='evidence')]},
 {'id':'REQ-5','kind':'requirement','group':'Design','rev':1,'date':'2026-05-20','text':'A patient reschedules unaided on first use.','evidence':'none yet'},
 {'id':'REQ-6','kind':'requirement','group':'Design','rev':1,'date':'2026-05-20','text':'The system offers open slots for the same visit type and confirms by message.','evidence':'Low','links':[L('depends-on','DEP-2',1)]},
 {'id':'DEP-2','kind':'dependency','group':'Engineering','rev':1,'date':'2026-05-06','text':'Scheduling system must expose open slots by visit type.','status':'open'},
 {'id':'TERM-R-BARRIER','kind':'term','group':'Research','rev':1,'date':'2026-05-22','text':'Rescheduling barrier: a structural obstacle outside the product (office hours, phone queues, staffing).','links':[L('same-as','EC-ACCESS',1,conditions='outside the product; structural',use='meaning mapping')],'adopted_by':'Sam Patel (Research lead)'},
 {'id':'EC-ACCESS','kind':'enterprise-concept','group':'Enterprise','rev':1,'date':'2026-01-10','text':'Access barrier: a structural obstacle preventing a person from obtaining a service they intend to use.'},
],
3: [
 {'id':'DD-1','kind':'design-decision','group':'Design','rev':1,'date':'2026-07-22','author':'Lee Chen','text':'One-tap reschedule from the reminder message as main path for all patients, with a visible "talk to staff" option.','alternatives':'portal login; phone tree','status':'proposed 2026-07-22; see DEC-2','links':[L('informed-by','FIND-1',1,conditions='all patients',use='direction'),L('informed-by','FIND-2',1,use='direction')],'comments':['2026-07-24 Dana Ortiz: "Looks great, love the direction! Let\'s see what testing says."','2026-07-25 Ana Brooks: "Approved from the clinic side, go for it."']},
 {'id':'TERM-D-FRICTION','kind':'term','group':'Design','rev':1,'date':'2026-07-25','text':'Friction point: extra effort inside a product flow (taps, screens, fields, waiting).','links':[L('same-as','EC-ACCESS',1,conditions='inside the product flow; effort',use='meaning mapping')],'adopted_by':'Lee Chen (Design lead)'},
],
4: [
 {'id':'EVAL-1','kind':'evaluation-result','group':'Design','rev':1,'date':'2026-08-14','text':'5 of 6 rescheduled unaided on first use; 1 missed the staff option.','evidence':'Moderate'},
 {'id':'REQ-5','kind':'requirement','group':'Design','rev':2,'date':'2026-08-20','text':'A patient reschedules unaided on first use.','evidence':'Moderate','links':[L('supported-by','EVAL-1',1,use='evidence')]},
 {'id':'DEC-2','kind':'decision','group':'Sponsor','rev':1,'date':'2026-09-03','decided_by':'Dana Ortiz','status':'approved','text':'One-tap reschedule is the primary path.','condition':'Staff option clearly visible for visit types that need staff.','links':[L('approves','DD-1',1),L('rests-on','EVAL-1',1,use='rationale')]},
 {'id':'FIND-3','kind':'finding','group':'Research','rev':1,'date':'2026-09-08','author':'Sam Patel','text':'85% of after-hours reschedule attempts fall between 5 pm and 9 pm; 10 of 12 interviewees accept a next-morning staff callback requested in the evening.','evidence':'Moderate','links':[L('refines','FIND-2',1,conditions='timing of after-hours attempts')]},
 {'id':'REQ-3','kind':'requirement','group':'Research','rev':2,'date':'2026-09-09','text':'Rescheduling works until 9 pm without staff; after that, patients can request a next-morning callback. Round-the-clock self-service not required.','evidence':'Moderate','change_reason':'FIND-3','links':[L('supported-by','FIND-2',1,use='evidence'),L('supported-by','FIND-3',1,use='evidence')]},
],
5: [
 {'id':'EVAL-1','kind':'evaluation-result','group':'Design','rev':2,'date':'2026-10-02','text':'Participant 4 excluded (staff member). 4 of 5 rescheduled unaided; the one who missed the staff option remains.','evidence':'Low'},
 {'id':'REQ-5','kind':'requirement','group':'Design','rev':3,'date':'2026-10-02','text':'(unchanged)','evidence':'Low','links':[L('supported-by','EVAL-1',2,use='evidence')]},
 {'id':'SURV-1','kind':'finding','group':'Research','rev':1,'date':'2026-10-28','text':'340 respondents, general population: 52% knew in advance, 41% forgot. Shift and irregular-hours workers (n=96): 71% knew in advance. Everyone else (n=244): 44% knew, 49% forgot.','evidence':'Moderate'},
 {'id':'CHAL-1','kind':'challenge','group':'Research','rev':1,'date':'2026-10-30','author':'Sam Patel','status':'open','text':'FIND-1 holds for shift workers but not the general population.','links':[L('challenges','FIND-1',1,conditions='general population'),L('based-on','SURV-1',1)]},
],
6: [
 {'id':'SPEC-D2','kind':'artifact','group':'Design','rev':1,'date':'2026-11-05','author':'Lee Chen','text':'Design spec v2: one-tap default for all patients and all reminders. Cites "most patients who miss already know in advance" and "5 of 6 unaided". Friction points removed: portal login, phone queue.','links':[L('informed-by','FIND-1',1,conditions='all patients',use='rationale'),L('supported-by','EVAL-1',1,use='evidence'),L('implements','DD-1',1)]},
 {'id':'ENG-H1','kind':'artifact','group':'Engineering','rev':1,'date':'2026-11-12','author':'Ravi Gomez','text':'Engineering handoff: rescheduling at any hour, 24/7 without staff; estimate includes high-availability tier (~40% of infrastructure cost). Slots API unconfirmed.','links':[L('implements','REQ-3',1),L('implements','REQ-6',1),L('depends-on','DEP-2',1)]},
],
}
packets_by_wave = {
 4: [{'id':'PK-SPONSOR','audience':'Dana Ortiz','resolved':'2026-09-05','refs':[['GOAL-1',2],['FIND-1',1],['DEC-2',1]]}],
 6: [{'id':'PK-DESIGN-SPEC','audience':'Lee Chen (Design)','resolved':'2026-11-05','refs':[['FIND-1',1],['EVAL-1',1],['DD-1',1],['REQ-2',1],['REQ-5',2]]},
     {'id':'PK-ENG-HANDOFF','audience':'Ravi Gomez (Engineering)','resolved':'2026-11-12','refs':[['REQ-3',1],['REQ-6',1],['DEP-2',1]]}],
}
store = {}; packets = []
for w in range(1, 7):
    for r in waves[w]:
        store.setdefault(r['id'], []).append(copy.deepcopy(r))
    packets += packets_by_wave.get(w, [])
    recs = [{'id': i, 'revisions': revs} for i, revs in store.items()]
    (OUT / f'graph-after-wave-{w}.json').write_text(json.dumps({'as_of_wave': w, 'records': recs, 'packets': packets}, indent=1))
    (OUT / f'wave-{w}-delta.json').write_text(json.dumps({'wave': w, 'new_or_revised': waves[w], 'new_packets': packets_by_wave.get(w, [])}, indent=1))
print('ok', len(store))
