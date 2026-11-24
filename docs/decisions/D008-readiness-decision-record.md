# D008: Readiness to build is a recorded human decision

Status: accepted by the user, 23 November 2026. Built on branch `claude/thesis-board`.

## Principle

The case board informs whether the work is ready to build; people decide. The
decision is recorded so the call, its reason and what the board showed at the time
are never lost.

## Rules

1. New record type `readiness-decision`, one record (`PROJECT-READINESS`) per
   project. Each call is a new revision; earlier calls and reasons are kept.
2. The call belongs to whoever holds Business direction decision rights (the
   decider or a delegate). Decision rights are not extended with a new type.
3. Outcomes: Ready to build, Ready with conditions (conditions required) or Not yet.
   A reason is required and the decider confirms explicitly.
4. The basis is computed on the server from shared records: the current intent
   version, every requirement's D004 level, measures and targets, open issues and
   conflicts, open requirement decisions and the two validation questions. The
   browser cannot supply or alter it.
5. A stale view cannot overwrite a newer call.
6. When the basis later changes, the board says so. The call stands until someone
   with the right records a new one; nothing changes it silently.
7. Recording readiness does not publish, approve requirements, send anything to
   Jira or Azure DevOps, or change any other record.
