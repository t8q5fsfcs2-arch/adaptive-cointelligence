# D012: Confidence is shown as three separate signals

Status: accepted by the user, 24 November 2026. Built on `claude/thesis-board`.
Builds on [D004](D004-requirement-evidence-level.md) and
[D008](D008-readiness-decision-record.md). The recorded confidence rating and its
rules are unchanged.

## Principle

People need to see how sure the project is, why, and what would make it surer,
without one number standing in for a judgment. Confidence is never merged with
accountability, and low confidence never blocks work.

## Rules

1. **Three signals together, never merged.** Each requirement shows:
   - the **confidence rating**: the requirement owner's recorded judgment for a
     named use (Not rated, Low, Moderate, High);
   - the **evidence level**: calculated from shared work (D004);
   - **validated by**: which teams have published work on the current version.
2. **Confidence rises only through reassessment.** A changed basis already marks a
   rating "Needs reassessment". Now, shared work published after a rating also
   prompts reassessment. The rating itself stays as recorded until the owner
   reassesses it.
3. **Roll-up is the weakest part.** An area is High only when every part is High
   (unchanged from D007).
4. **Always say what would raise it.** The evidence calculation returns what the
   next level needs, from the same facts, and the display shows it.
5. **Low confidence never blocks.** Moving ahead stays allowed and is recorded by
   the readiness call (D008).
6. **Levels, not percentages.**

## How it is built

- `requirement_evidence.py` returns `raise_to` (next level and what it needs). The
  calculation and thresholds are unchanged.
- `requirement_assessments.py` returns `reassess` for each use when shared work on
  the requirement was published after the rating. Reading writes nothing.
- `requirement-evidence.js` renders the three signals above the evidence detail,
  wherever a requirement is opened.

## Not done

- An AI-drafted reassessment for the owner to confirm. Reassessment uses the
  existing recorded assessment.
- "Validated by" on the home board; it appears on each requirement.

## Later change

Under [D014 revision 2](D014-chained-packets-and-dependency-difference.md) the
signals are labelled **Evidence coverage** (was Evidence level) and **Contributions
from** (was Validated by), because counting shared work measures coverage, not
quality, and publication is not validation. The coverage calculation now also counts independent sources (see D004). The AI may
propose a scoped assessment with reasons; the owner still records the official
rating.
