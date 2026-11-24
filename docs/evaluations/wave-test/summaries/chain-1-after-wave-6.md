# Project memory: Riverside Clinics, Fewer Missed Appointments

Sources: docs 01-18. Current to 12 Nov 2026.

## People
- Dana Ortiz, Director of Operations: sponsor, **sole decision owner**.
- Sam Patel: Research lead. Lee Chen: Design lead. Ravi Gomez: Engineering.
- Ana Brooks: Northside clinic manager (**not a decision owner**). Priya Nair: Operations Analytics.

## Intent (Dana, 6 May)
- Cut missed visits **16% to 11%** within six months by letting patients reschedule themselves ("at any hour"; see R3). Reminders stay, not the main lever.
- Superseded (2 Mar): 18%, 48-hour reminders, target 10%. Priya (22 Apr): true rate 16%; target 11%, no stated reason.
- **Under challenge (Sam, 30 Oct):** April finding fails for general population. **No change proposed or decided.**

## Decisions
- **3 Sep (Dana): one-tap reschedule from the reminder is the primary path.** Condition: staff option clearly visible for visit types needing staff. Basis: August test (corrected, weaker).
- Not approvals: Dana 24 Jul "see what testing says"; Ana 25 Jul "approved".

## Evidence
- **Readout (Sam, 10 Apr).** 12 interviews, all shift/irregular workers, evening clinics Northside and Eastgate. 9/12 knew in advance; 2/12 forgot. Rescheduling, not remembering, is the barrier (moderate). 7/12 tried after 5 pm.
- **Usability test (14 Aug, v0.2), corrected 2 Oct.** Participant 4 was staff, excluded: **4/5** unaided (not 5/6); 1 missed "talk to staff". R5 evidence **low**.
- **Call logs (8 Sep).** 85% of after-hours attempts 5-9 pm; 10/12 interviewees accept next-morning callback.
- **Survey (28 Oct).** 340 general-population patients who missed. Overall 52% knew, 41% forgot, 7% other. Shift workers (n=96) 71% knew; others (n=244) 44% knew, **49% forgot**.
- **Challenge (Sam, 30 Oct, to Dana and Lee).** April finding holds for shift workers only. Not withdrawn.

## Requirements
- R2. Reschedule without phoning. Basis: April readout (challenged).
- **R3 current (Sam, 9 Sep):** "Rescheduling works until 9 pm without staff; after that, patients can request a next-morning callback." Supersedes v1 (20 May) "24/7 without staff". **No Dana ratification**; narrows "any hour".
- R5. Unaided first-use reschedule. Evidence **low** (4/5).
- R6. Same-visit-type slots, confirm by message. Slots API: vendor says Q1, **unconfirmed** (Ravi, 12 Nov).

## Design
- **One-tap proposal (Lee, 22 Jul; decided 3 Sep):** from reminder, all patients, visible "talk to staff". Rejected: portal, phone tree.
- **Spec v2 (Lee, 5 Nov):** default for all patients and all reminder messages; **Stale basis:** cites "most who miss know in advance" (challenged; 44% outside shift workers) and "5 of 6" (corrected to 4/5). Does **not mention** Dana's staff-option condition or the after-9-pm callback. Uses unapproved "friction points".
- Cautions: "all patients" exceeds research base; reminder is entry-channel dependency.

## Engineering handoff (Ravi, 12 Nov)
- **Built to superseded R3 v1** ("any hour, 24/7, without staff"). Estimate includes high-availability tier for slots service, **about 40% of infrastructure cost**. Current R3 may not need it; callback not scoped.

## Glossary conflict (unresolved)
- **Rescheduling barrier** (Sam): obstacle **outside the product**. **Friction point** (Lee): effort **inside a product flow**. Both mapped "same as" **Access barrier**; neither approved; cannot both be. Rescheduling barrier fits better ("narrower than"?); Friction point at most "related to".

## Open tensions
- Self-rescheduling lever rests on shift workers; reminders may matter more for others.
- Spec v2 and handoff propagate outdated facts (5/6, April finding unqualified, R3 v1). Need correction before build.
- One-tap basis weak; Dana not asked to reconsider. Unratified R3 vs intent's "any hour" may explain Ravi's reading.
- Only Dana decides; a challenge, spec or memo changes nothing by itself.

## Open questions
- Will Dana revisit intent framing and reminders' role, drop "any hour", ratify R3?
- Will Ravi re-estimate to current R3 (incl. callback staffing)? Slots API date?
- Will Lee restore staff-option condition and update spec rationale?
- 16% by clinic/group; basis for 11%; shift workers' share of misses; visit types needing staff?
- Retest one-tap? Resolve Access barrier mappings.

## Timeline
2 Mar kickoff; 10 Apr readout; 22 Apr baseline; 6 May intent; 20 May requirements v1; 22 Jul one-tap; 14 Aug test; 3 Sep decision; 8 Sep call logs; 9 Sep R3; 2 Oct correction; 28 Oct survey; 30 Oct challenge; 5 Nov spec v2; 12 Nov handoff.
