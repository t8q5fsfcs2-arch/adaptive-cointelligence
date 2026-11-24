# D003: Suggestions are editable and require validation

Status: accepted by the user, 21 November 2026; rule 7 added 22 November 2026.
Universal across the product.

## Principle

As much content as possible can reach a person as a suggestion drawn from found
knowledge: sources, earlier work, domain knowledge and AI interpretation. Every
suggestion is editable, and the person knows they must validate it before it
locks in.

## Rules

1. **Arrives as a suggestion.** Suggested content is visibly marked as suggested,
   says where it came from (which source, reply, review or rule), and is never
   presented as the person's own or as evidence.
2. **Fully editable.** The person can change any part before validating it.
   Editing does not validate it.
3. **Validation is explicit.** A clear action (accept, confirm, save) locks the
   content in as the person's own, recorded as a new version with who validated
   it, when, and what it was suggested from.
4. **Unvalidated content does not count.** Suggestions never complete a
   question, enter a shared package, satisfy a review or support a decision
   until validated. Dismissing a suggestion is allowed and recorded.
5. **Locked means versioned, not frozen.** Later changes create a new version;
   the validated version and its origin remain in history.
6. **One visual language.** The same suggested, edited and validated states look
   and behave the same on every screen.
7. **The person's work stays editable, and the loop repeats.** Anything a person
   works on in a workbench or in Business Intent can be edited by them. They can
   edit, send the current version back to the AI partner, receive suggestions,
   and edit again, as many times as they like. The AI partner never overwrites
   the person's text; its reply arrives as a new suggestion against the exact
   version it was given, and only the person's validation changes their work.
   Published and shared versions are not edited in place: revising them starts a
   new version (rule 5).

## Fit with the backend

This matches the existing architecture (AI proposes, humans govern) and existing
mechanisms that store AI-origin, edited and confirmed status: AI partner advice,
Business Intent field suggestions, goals, scaffold tailoring, requirement
assistance, brief refinement, plan edits from chat and building-block capture.
Presentation work applies one consistent pattern over them. Any new source of
suggestions (for example, AI-proposed building blocks from uploaded sources)
must follow these rules and needs its own decision because it adds behavior.
