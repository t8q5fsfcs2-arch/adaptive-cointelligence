# Project memory: Riverside Clinics, Fewer Missed Appointments

Sources: w1-w6. All research synthetic.

## People
- Dana Ortiz: Director of Operations; sponsor, decision owner.
- Sam Patel: Research lead.
- Lee Chen: Design lead.
- Ravi Gomez: Engineering lead.
- Ana Brooks: Northside clinic manager; contributor, no decision rights.
- Priya Nair: Operations Analytics.

## Business intent (decided 6 May, Dana, steering; in force)
- Cut missed visits 16% to 11% in six months by letting patients reschedule themselves **at any hour**. Reminders stay, not main lever.
- Superseded (2 Mar): reminders, 18% to 10%; "patients forget".
- **Challenged 30 Oct (Sam)**; no change proposed or decided.

## Baseline
- 22 Apr, Priya: 16%, not 18% (same-day cancellations double counted). Unknown: period, per-clinic split.

## Research evidence
- Readout 10 Apr (Sam): 12 interviews, Northside and Eastgate only, all shift/irregular-hours workers. 9 knew in advance, 2 forgot, 1 unexplained. Finding: barrier is rescheduling, not remembering.
- 18 Apr: 7 of 12 tried rescheduling after 5 pm.
- Call logs 8 Sep: 85% of after-hours attempts 5-9 pm. 10 of same 12 would accept next-morning callback. Period, clinics, volumes unknown.
- **Survey 28 Oct:** 340 general-population missers. 52% knew in advance, 41% forgot. Shift workers (n=96): 71% knew. Others (n=244): 44% knew, 49% forgot.
- **Challenge 30 Oct (Sam to Dana, Lee):** April finding holds for shift workers only; May framing may need revisiting.

## Usability test, 14 Aug (prototype v0.2)
- **Corrected 2 Oct (Sam):** one participant was staff, excluded. Now 4 of 5 unaided (was 5 of 6); 1 of 5 missed "talk to staff". Evidence low; profile not stated.

## Requirements
- R2. Reschedule without phoning.
- R3 v2 (Sam alone, 9 Sep; current): self-service until 9 pm, then next-morning callback request. Superseded v1 (20 May): 24/7 without staff.
- R5. Unaided on first use. Evidence low.
- R6. Open slots of same visit type, message confirmation. Slots API: vendor says Q1, unconfirmed (Ravi, 12 Nov).
- R1, R4 missing, unexplained.

## Design
- Proposal 22 Jul (Lee): one-tap, visible "talk to staff".
- **Decided 3 Sep (Dana, steering):** one-tap from reminder is primary path, **provided** staff option clearly visible for visit types needing staff. Basis: pre-correction 5 of 6; not revisited.
- **Spec v2, 5 Nov (Lee):** one-tap default for all patients and all reminders; removes portal login, phone queue. Rationale cites stale evidence ("most know in advance"; "5 of 6"). Omits the staff option required by the 3 Sep decision.

## Engineering
- **Handoff 12 Nov (Ravi):** builds R3 as 24/7 without staff (superseded v1). Estimate includes high-availability slots service, about 40% of infrastructure cost. Also building R6. No callback flow.

## Glossary mappings
- Research (22 May, Sam alone): Rescheduling barrier = structural obstacle outside product; "same as" Access barrier.
- Design (25 Jul, Lee alone): Friction point = extra effort inside a product flow; also "same as" Access barrier.

## Points to watch (my observations, not decided)
- Spec v2 and handoff ignore 2 Oct correction, survey, R3 v2.
- Spec v2 drops the staff-option condition; visit types needing staff undefined; no retest.
- 40% HA spend targets superseded R3 v1. Intent ("at any hour") and R3 v2 (9 pm cutoff) still conflict; now costly. Needs decision before build.
- Forgetting drives about half of non-shift-worker misses; reminders may deserve more weight. Only Dana decides intent.
- Mapping conflict: Friction point "same as" structural Access barrier is contradictory; at most "related to". Rescheduling barrier likely "narrower than". Approval route unclear.

## Next steps
- Dana: reopen intent ("at any hour" vs R3 v2)? Reconsider 3 Sep decision?
- Lee: correct spec v2 rationale; restore staff option.
- Ravi: re-scope to current R3 (or await Dana); revisit HA cost; confirm slots API.
- Define staff-needed visit types; retest, larger profiled sample.
- Design callback (unscoped); confirm staff capacity.
- Per-clinic survey and call-log data (interviews: 2 of 4 clinics).
- Clarify R1, R4; reconcile mappings.

## Timeline
- 03-02 kickoff; 04-10 readout; 04-22 baseline; 05-06 intent; 05-20 requirements v1; 07-22 design proposal; 08-14 test; 09-03 one-tap decided; 09-09 R3 v2; 10-02 test corrected; 10-28 survey; 10-30 challenge; 11-05 spec v2; 11-12 engineering handoff.
