# Wave test: how context holds up as a project evolves

Run 25 November 2026 on synthetic data. Evidence for proposed decision
[D014](../decisions/D014-chained-packets-and-dependency-difference.md).
Everything used is in [wave-test/](wave-test/).

## Question

As a project evolves across groups, does meaning stay traceable and comparable
without structure? Or does it need chained packets with shared identifiers and typed,
revision-pinned links, as D014 proposes?

## Setup

One clinic project, March to November 2026, released in six waves (18 documents).
It involves Research, Design, Engineering and the sponsor. Six problems were planted
for the setups to find:

| # | Planted problem | Where it appears |
|---|---|---|
| 1 | **Scope widening.** Research's finding covers shift workers. Design applies it to all patients. | Waves 1, 3, 6 |
| 2 | **Mapping conflict.** Research's "rescheduling barrier" (structural, outside the product) and Design's "friction point" (effort inside the flow) are both mapped "same as" the enterprise concept *Access barrier*. | Waves 2, 3 |
| 3 | **Lineage.** The after-hours need was read as 24/7 in May and narrowed to "until 9 pm plus callback" in September. | Waves 2, 4 |
| 4 | **Revision skew.** The design spec still cites 5 of 6 after the correction to 4 of 5. The engineering handoff builds to 24/7 after the requirement was narrowed. | Waves 5, 6 |
| 5 | **Propagation.** A survey challenges the April finding. | Wave 5 |
| 6 | **Drift.** An unchanged fact: the 18 April email (7 of 12 tried after 5 pm; evening spike in abandoned calls). | Wave 1 |

Three setups were run, each twice by fresh model instances that had not seen the
answers:

- **A. Documents only.** All 18 documents, read again at the end.
- **B. Rolling memory.** After each wave, a fresh instance read only its previous
  memory (at most 700 words) plus that wave's documents, and rewrote the memory. The
  final answers came from the memory alone. This is how most AI tools carry context
  forward today.
- **C. Graph.** Typed blocks with pinned links and packets, plus a dependency
  difference report computed by a script with no model involved
  (`tools/dependency_diff.py`).

There were seven questions, covering propagation, translation, mapping, lineage,
revision skew, drift and authority.

## Results

| Question | A. Documents | B. Rolling memory | C. Graph |
|---|---|---|---|
| Q1 Propagation | Correct | **Wrong in both runs.** Invented dependencies: the engineering handoff, R3 and R6 were listed as affected. | Correct, including the indirect decision and both packets |
| Q2 Translation (scope) | Correct | Correct | Correct. The difference report flagged it as a conflict before any model read it. |
| Q3 Mapping | Correct | Correct | Correct, and flagged by the script |
| Q4 Lineage | Correct | Mostly correct. One run attributed claims to the spec that the documents do not make. | Correct, revision by revision |
| Q5 Revision skew | Correct, except it could not see packet pins | **Wrong in both runs.** Invented links, such as the handoff "propagating 5 of 6". | Correct and complete. Only setup that caught the design packet pinning an old requirement revision. |
| Q6 Drift (unchanged fact) | Correct, exact numbers | **Failed.** One run had lost the 18 April finding entirely. The other kept "7 of 12" but lost the call-log spike. | Correct numbers. Noted that the store records a finding, not "an email". |
| Q7 Authority | Correct | One run dropped the July non-approvals | Correct |
| Agreement between the two runs | High | **Low.** Different lists of what is affected | Highest. Near-identical answers. |

## What it shows

1. **Rolling memory is the failure mode, and it fails the way D014 predicts.** Each
   rewrite compressed and reinterpreted. By wave 6 the memory had:
   - dropped an unchanged fact;
   - invented dependencies that were never stated;
   - produced different pictures in two runs.

   The memory writers did notice the conflicts as they arrived (scope, mapping, skew).
   Noticing is not the problem; keeping it straight across rewrites is.
2. **The graph made the important differences deterministic.**
   - Scope conflict, mapping conflict, revision skew and propagation were computed by
     a script, identically every time, before any model read them.
   - The model's job shrank to explaining them.
   - That is what allows alerts, queries and audit without a model in the loop.
3. **Rereading all documents still works at this size.** Setup A matched C on almost
   everything. Its limits did show:
   - it cannot see packet pins;
   - every answer is rebuilt from scratch, so nothing is shared or persistent between
     people or runs;
   - the cost grows with the whole corpus every time anyone asks.
4. **The graph only knew what was captured.**
   - Setup C caught the scope conflict because the links carried conditions ("all
     patients" versus "shift workers"). If Design had linked without conditions, the
     script would have seen agreement.
   - The structure lost the document's form ("an email").
   - So the AI should propose conditions on links and people should confirm them
     (D003). And blocks must keep their source documents.

## What it does not show

- **Scale.** 18 documents fit in one read. With hundreds across several projects,
  setup A cannot reread everything. That is where a graph should pull clearly ahead.
  Not yet tested.
- **Cost.** Not measured fairly at this size.
- **Fairness limits.**
  - I wrote the documents, the graph, the script and the key.
  - The graph records interpretations explicitly (conditions on links) that documents
    only imply. That is the point of D014, but it means C's advantage depends on those
    interpretations being captured in practice.

## Next test

Scale it up:
- 5 projects and about 200 documents;
- one concept shared across projects through the enterprise layer;
- a question that must be answered with no model in the loop.
