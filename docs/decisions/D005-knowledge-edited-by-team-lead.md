# D005: Team knowledge is edited only by the team's lead

Status: accepted by the user, 23 November 2026.
Narrows the earlier "domain leader or administrator" rule for knowledge entries.

## Principle

Each team's knowledge (terms, categories, relationships, standards and practices)
guides its AI partner and its assessments. It belongs to the team, so the team's
lead curates it.

## Rules

1. Only a lead of the team (the domain's `leaders`) can save that team's knowledge
   entries. Everyone in the project can read every team's knowledge.
2. Administrators and development-mode settings access do not grant knowledge
   editing. They still manage team setup: the team's name, purpose, members and
   leads. To change who curates knowledge, change the team's leads.
3. The permission is enforced in the backend and shown in the interface: people
   who are not the lead see the knowledge read-only, with no edit controls.
4. Earlier knowledge versions and the assessments that used them are unchanged.
