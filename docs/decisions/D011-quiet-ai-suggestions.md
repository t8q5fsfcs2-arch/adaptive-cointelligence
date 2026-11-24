# D011: Quiet AI partner suggestions

Status: accepted by the user, 24 November 2026. Built on `claude/thesis-board`.

## Principle

The AI partner's suggestions on a person's private work are available at the edge
of the workbench and never interrupt the work. The only signal is a count on the
Suggest instrument. Nothing pops up and nothing is inserted into the conversation.

## Decisions by the user

- Suggestions arrive **with the AI partner's replies**. No separate AI calls.
- Each person can turn them **off for themselves**. On by default.
- With **no model connected**, the instrument says the AI partner is unavailable
  and shows nothing in its place.

## How it is built

1. The AI partner already returns up to four grounded suggestions with each reply
   and saves them in the review of that reply. D011 surfaces those; it adds no
   model call, prompt or output type.
2. The Suggest instrument lists up to three suggestions from current saved
   replies on this work, newest first, each marked "Suggested · AI partner"
   (D003). A suggestion disappears on its own when the work it was about changes.
3. Each has Show me (opens the saved review with its basis), Ask about it (puts
   its question in the composer; the person still sends) and Dismiss. "Dismiss
   all" clears the list.
4. One new private record per person and team, `suggestion-preferences`, holds the
   switch and the dismissals. Only the person's own suggestions can be dismissed.

## Limits

Suggestions are never counted, never shown to anyone else, and never block or
change sharing. The panel cannot edit a draft, the sharing report or any record
other than the person's own preferences.

## Not done

The approved brief described good-practice checks (one source, no method, no
counterexample). Today's replies are asked for "consequential suggestions" on
evidence, intent and the next team's needs, which overlap with that but are not
the same list. Steering replies toward explicit practice checks would change the
AI partner's instructions and therefore its answers, so it is left for a separate
decision.
