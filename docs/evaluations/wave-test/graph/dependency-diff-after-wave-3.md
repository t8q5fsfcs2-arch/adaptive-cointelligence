# Dependency difference report (computed)

## Shared identifiers: signatures by group

### EC-ACCESS (latest rev 1)
- Research: TERM-R-BARRIER --same-as--> EC-ACCESS rev 1; conditions: outside the product; structural; use: meaning mapping
- Design: TERM-D-FRICTION --same-as--> EC-ACCESS rev 1; conditions: inside the product flow; effort; use: meaning mapping
- **Classification: CONFLICT (scope or conditions differ across groups: ['inside the product flow; effort', 'outside the product; structural'])**

### FIND-1 (latest rev 1)
- Research: OBS-P07 --supports--> FIND-1 rev 1; conditions: (none); use: (none)
- Research: REQ-2 --supported-by--> FIND-1 rev 1; conditions: shift and irregular-hours workers; use: evidence
- Sponsor: DEC-1 --rests-on--> FIND-1 rev 1; conditions: (none); use: rationale
- Design: DD-1 --informed-by--> FIND-1 rev 1; conditions: all patients; use: direction
- **Classification: CONFLICT (scope or conditions differ across groups: ['all patients', 'shift and irregular-hours workers'])**

### FIND-2 (latest rev 1)
- Research: REQ-3 --supported-by--> FIND-2 rev 1; conditions: (none); use: evidence
- Design: DD-1 --informed-by--> FIND-2 rev 1; conditions: (none); use: direction
- Classification: COMPLEMENT (different uses: direction, evidence)

## Meaning mappings to enterprise concepts
- EC-ACCESS: Research term TERM-R-BARRIER same-as, conditions: outside the product; structural
- EC-ACCESS: Design term TERM-D-FRICTION same-as, conditions: inside the product flow; effort
- **MAPPING CONFLICT on EC-ACCESS: groups map same-as under different conditions; enterprise queries will merge different meanings.**

## Revision skew (current work pinned to superseded revisions)

## Propagation from open challenges

## Revision history (lineage)

### GOAL-1
- rev 1 (2026-03-02): Automated reminders cut missed visits from 18% to 10% within six months of launch.
- rev 2 (2026-05-06): Cut missed visits from 16% to 11% within six months by letting patients reschedule themselves at any hour; reminders not the main lever. [basis/reason: DEC-1]
