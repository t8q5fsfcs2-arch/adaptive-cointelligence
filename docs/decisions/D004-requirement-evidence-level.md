# D004: Requirements are read-only tanks with a computed evidence level

Status: accepted by the user, 22 November 2026.
Partly supersedes the "no calculated confidence" guidance in
an earlier decision record (ADR 0065) and the earlier confidence framework, for the new evidence
level only. The human-recorded confidence rating and its rules are unchanged.

## Principle

The Requirements area is where requirements live once approved and shared. It is
read-only. Requirements may start with very low confidence. Each one is like a
tank that any participating team can fill: published work adds evidence, and
Decisions & issues is the asynchronous meeting space where the group challenges,
refines and decides. All suggesting and deciding of requirements happens there.

## Rules

1. **Read-only Requirements area.** No requirement wording is edited on the
   Requirements page. New or changed requirements are proposed on an issue and
   decided by the person with decision rights. (Already enforced by the backend
   after publication; this records it as a product rule.) The sponsor's private
   starting requirements setup in Business Intent stays editable under D003.
2. **Evidence level is computed, labelled and explained.** Each requirement shows
   an Evidence level (Empty, Low, Moderate or High) calculated only from shared
   records, with every factor and reason visible:
   - published contributions that reference the requirement, and how many teams
     they come from;
   - how many reference the current version rather than an earlier one;
   - how recent the newest evidence is;
   - open contradictions (challenge or conflict issues), open gaps (gap or
     information-need issues) and open dependencies on the requirement;
   - issues on it that were worked through and resolved.
   Logic quality is represented by the open contradictions, gaps and
   dependencies. No AI or model call is involved.
3. **Calculation (version 1).**
   - Empty: no published contribution references the requirement.
   - Low: any open contradiction, or no evidence on the current version, or the
     newest evidence is older than 180 days.
   - High: at least two contributions on the current version, from at least two
     teams, newest evidence within 90 days, and no open contradictions or gaps.
   - Moderate: everything else.
   Thresholds are named constants in one service and are versioned with it.
4. **Separate from recorded confidence and approval.** The evidence level is a
   projection recalculated on read. It is never stored as an assessment, never
   shown as or copied into the recorded confidence rating, never approves,
   blocks or authorizes anything, and never changes a requirement. Approval
   status, recorded confidence and evidence level appear as three distinct items.
5. **Shared audience only.** Only published contributions and shared issues
   count. Private drafts, chats and building blocks never affect the level, so
   every member of the project sees the same level for the same records.
6. **Filling the tank is shown as an invitation.** The display says how a team
   adds evidence (share work that references the requirement) and where to
   challenge or refine it (Decisions & issues). Packet membership or reference
   alone does not establish support, dependency or approval; the label says
   "references", not "supports".
