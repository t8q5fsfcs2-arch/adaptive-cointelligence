# D013: Building blocks are organised for long-term knowledge

Status: accepted by the user, 24 November 2026. Built on `claude/thesis-board`.

## Principle

Building blocks are the units of knowledge a workbench produces. They serve the
enterprise later only if a future project can tell what was seen from what was
concluded, and whether a block fits its own situation.

## Decisions

1. **Four families** organise the types: Evidence, Direction, Open, Outputs.
2. **Each team's types lead.** A domain profile may list `block_types`; otherwise
   defaults apply (Research: observation, finding, user situation, user flow,
   hypothesis, open question, lesson. Design: design decision, evaluation result,
   artifact, user story, user flow, dependency, lesson). Every other type stays
   available under "More types", and any type that already holds a block is shown.
3. **Four new types:**
   - **Observation:** what was seen, with its source, separate from the finding.
   - **Design decision:** the choice, the alternatives and the rationale.
   - **Evaluation result:** what was tested, with whom, against which criteria.
   - **Lesson:** scoped learning for another project, with conditions and limits.
4. **A shared "Where this applies" footer** on every type: people or role,
   situation, time or period, and how sure. A type that already has an equivalent
   field does not get a duplicate.

## Compatibility

No type or field was removed or renamed. Existing blocks, links, publication and
privacy are unchanged. Blocks stay private until published with work.

## Not done

- The AI partner filling the footer from the conversation for the person to
  confirm. People fill it in, or place selected chat text into a field with the
  existing capture.
- Review of the type list by research and design practitioners. The list is a
  starting point and should be checked with them.
