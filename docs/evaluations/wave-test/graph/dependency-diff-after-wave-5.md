# Dependency difference report (computed)

## Shared identifiers: signatures by group

### EC-ACCESS (latest rev 1)
- Research: TERM-R-BARRIER --same-as--> EC-ACCESS rev 1; conditions: outside the product; structural; use: meaning mapping
- Design: TERM-D-FRICTION --same-as--> EC-ACCESS rev 1; conditions: inside the product flow; effort; use: meaning mapping
- **Classification: CONFLICT (scope or conditions differ across groups: ['inside the product flow; effort', 'outside the product; structural'])**

### EVAL-1 (latest rev 2)
- Design: REQ-5 --supported-by--> EVAL-1 rev 2; conditions: (none); use: evidence
- Sponsor: DEC-2 --rests-on--> EVAL-1 rev 1; conditions: (none); use: rationale
- **Classification: CONFLICT (revision skew)**

### FIND-1 (latest rev 1)
- Research: OBS-P07 --supports--> FIND-1 rev 1; conditions: (none); use: (none)
- Research: REQ-2 --supported-by--> FIND-1 rev 1; conditions: shift and irregular-hours workers; use: evidence
- Research: CHAL-1 --challenges--> FIND-1 rev 1; conditions: general population; use: (none)
- Sponsor: DEC-1 --rests-on--> FIND-1 rev 1; conditions: (none); use: rationale
- Design: DD-1 --informed-by--> FIND-1 rev 1; conditions: all patients; use: direction
- **Classification: CONFLICT (scope or conditions differ across groups: ['all patients', 'general population', 'shift and irregular-hours workers'])**

### FIND-2 (latest rev 1)
- Research: REQ-3 --supported-by--> FIND-2 rev 1; conditions: (none); use: evidence
- Research: FIND-3 --refines--> FIND-2 rev 1; conditions: timing of after-hours attempts; use: (none)
- Design: DD-1 --informed-by--> FIND-2 rev 1; conditions: (none); use: direction
- Classification: COMPLEMENT (different uses: direction, evidence)

## Meaning mappings to enterprise concepts
- EC-ACCESS: Research term TERM-R-BARRIER same-as, conditions: outside the product; structural
- EC-ACCESS: Design term TERM-D-FRICTION same-as, conditions: inside the product flow; effort
- **MAPPING CONFLICT on EC-ACCESS: groups map same-as under different conditions; enterprise queries will merge different meanings.**

## Revision skew (current work pinned to superseded revisions)
- DEC-2 (Sponsor) uses EVAL-1 rev 1; latest is rev 2 (2026-10-02).

## Propagation from open challenges

CHAL-1 challenges FIND-1 (general population). Dependents:
- direct: DD-1 (Design, design-decision)
- direct: DEC-1 (Sponsor, decision)
- direct: REQ-2 (Research, requirement)
- indirect (depth 2): DEC-2 (Sponsor, decision)
- indirect (depth 2): GOAL-1 (Sponsor, goal)
- packet: PK-SPONSOR

## Revision history (lineage)

### GOAL-1
- rev 1 (2026-03-02): Automated reminders cut missed visits from 18% to 10% within six months of launch.
- rev 2 (2026-05-06): Cut missed visits from 16% to 11% within six months by letting patients reschedule themselves at any hour; reminders not the main lever. [basis/reason: DEC-1]

### REQ-3
- rev 1 (2026-05-20): Rescheduling works at any hour, 24/7, without staff. [basis/reason: Research reads "after 5 pm" as a need for round-the-clock self-service.]
- rev 2 (2026-09-09): Rescheduling works until 9 pm without staff; after that, patients can request a next-morning callback. Round-the-clock self-service not required. [basis/reason: FIND-3]

### REQ-5
- rev 1 (2026-05-20): A patient reschedules unaided on first use.
- rev 2 (2026-08-20): A patient reschedules unaided on first use.
- rev 3 (2026-10-02): (unchanged)

### EVAL-1
- rev 1 (2026-08-14): 5 of 6 rescheduled unaided on first use; 1 missed the staff option.
- rev 2 (2026-10-02): Participant 4 excluded (staff member). 4 of 5 rescheduled unaided; the one who missed the staff option remains.
