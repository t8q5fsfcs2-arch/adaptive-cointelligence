# Decision and action log

A running record of what was decided and what was done on the `claude/northstar-ux`
redesign and the `claude/thesis-board` branch built from it, newest first. Formal product and architecture decisions have their own
records in [decisions](decisions/README.md); this log points to them.

**Decision** is something the owner chose or approved. **Action** is work done.
Commits are on `claude/northstar-ux` unless noted. "Pushed" means on GitHub.

## Open items

- `given-northstar` tag is not on GitHub (the push connection drops); the given
  version is preserved as branch `claude/northstar` (654febf). Push it with
  `git push origin given-northstar` from the local clone.
- Demo data on the Mac predates the later seed fixes; reseed to see them.
- The live AI partner needs a model connection; without one, AI actions are
  disabled or explain why.

## 2026-11-24 (night)

- **Decision:** refine the prototype from an evaluation of the current build
  against first-time reviewer feedback. All items approved by the owner.
- **Decision:** the shared space is named "Decisions & Issues" everywhere; the
  panel on Requirements becomes "Explain these requirements".
- **Decision:** confidence is shown as three separate signals
  ([D012](decisions/D012-confidence-signals.md)); building blocks get families,
  per-team sets, four new types and a "Where this applies" footer
  ([D013](decisions/D013-knowledge-block-families.md)).
- **Action:** Home leads with "Waiting on you"; the Working brief opens with what
  was handed over; clearer workbench actions; a summary before sharing Business
  Intent; counts, version labels, file areas, phone rail and readiness label
  cleaned up.
- **Open:** AI-drafted reassessment and AI-filled "applies to" fields; review of
  block types by research and design practitioners.

## 2026-11-24 (evening)

- **Decision:** write a developer guide for backend and full-stack engineers,
  framed by the two spaces (private workbenches, shared space) and the boundary
  between them. Nothing about any client or industry beyond the clinic demo.
- **Action:** added [the developer guide](developer-guide.md) and linked it from
  the docs index. Documentation only; no behaviour changed.
- **Open:** whether to add the four prototype contracts the guide proposes
  (outbox and stale marking, an enforced agent contract, a retrieval seam, a
  behaviour test pack).

## 2026-11-24 (afternoon)

- **Decision:** remove the round AI partner icon everywhere.
- **Decision:** the workbench becomes a cockpit: conversation dominant, next
  moves and tools on an instrument rail. Recorded as
  [D010](decisions/D010-workbench-cockpit.md).
- **Action:** `cockpit.js` adds the heads-up strip, the instrument rail and the
  Next moves, Reviews and Updates panels. All earlier workbench actions remain.
- **Decision:** quiet AI partner suggestions: with its replies, a per-person off
  switch, and "unavailable" when no model is connected. Recorded as
  [D011](decisions/D011-quiet-ai-suggestions.md).
- **Action:** a Suggest instrument surfaces the suggestions replies already
  return, with Show me, Ask about it and Dismiss. No new model call or prompt.
- **Open:** steering replies toward explicit good-practice checks.

## 2026-11-24 · branch `claude/thesis-board`

- **Decision:** the owner approved governed meaning across domains and the
  enterprise: an enterprise store, Semantic services and enterprise steward roles,
  people first (no API yet), and boundaries, reach, typed mappings and meaning
  proposals. Recorded as [D009](decisions/D009-meaning-governance.md).
- **Action:** four mockups added to the design canvas (administrator overview in
  light and dark, a concept opened, a facilitated session).
- **Action (D009 step 1):** terms and categories can carry includes, excludes,
  "not to be confused with" and a reach level. Leads set project or domain reach;
  wider reach is refused until proposals exist. Knowledge shows boundaries and a
  reach ladder; active boundaries reach the team's AI partner as guidance. The
  synthetic demo seeds two bounded concepts.
- **Action (D009 step 2):** `meaning.py` adds meaning proposals between teams:
  typed mappings (both leads decide) and sharing a concept (owning lead decides),
  with withdraw, retire and a stale-wording guard. Knowledge shows an "Across
  teams" panel and section; proposals waiting on a lead appear on Project home.
- **Open:** whether approved mappings and shared concepts should also reach the
  other team's AI partner. Not built; needs the owner’s decision.
- **Action (D009 step 3):** `enterprise.py` adds the enterprise store, the two
  roles, proposals for wider reach (team lead and steward decide as two people)
  and enterprise concepts. New Enterprise context page; "Propose wider reach" on a
  concept; decisions waiting on a person appear on Project home.
- **Decision:** the owner left the order to Claude; adoption came before the
  facilitated session because it is what makes enterprise concepts usable.
- **Action:** `adoption.py` lets a team lead adopt an enterprise concept at a
  pinned version, move to a newer one after comparing wording, or drop it. The
  Knowledge page shows a team's enterprise concepts; the overview shows use.
- **Open:** AI-use counts on the overview; whether adopted, shared and mapped
  concepts reach a team's AI partner; no roles are assigned until an
  administrator does it.
- **Action (D009 step 4):** facilitated sessions. Semantic services runs an agenda
  of topics and a team's open proposals; deciders decide from the session; the
  facilitator never does. Team leads reach an open session from Knowledge.
- **Action:** pushed `claude/thesis-board` (D009 steps 1 to 4 and adoption) to
  GitHub on the owner’s request.
- D009's four steps are built. Still open: AI use of adopted, shared and mapped
  concepts; AI-use counts; AI suggestions inside a session.

## 2026-11-23 (late night) · branch `claude/thesis-board`

- **Decision:** bring back the two details the stage cards carried.
- **Action:** case strength gains a Handoff line (requirements approved, items
  staged for Jira and Azure DevOps, simulated notice, link to Handoff); the mission
  line credits the latest intent revision ("Intent v2 from Jordan's finding"),
  using the source work's owner as Business Intent does.
- **Check:** every visible action on 19 screens compared with `claude/northstar-ux`;
  none missing.
- **Action:** pushed `claude/thesis-board` (7b973bf) and `claude/northstar-ux`
  (6c211e6) to GitHub on the owner’s request.

## 2026-11-23 (night) · branch `claude/thesis-board`

- **Decision:** the owner approved a new record type for the readiness call.
  Recorded as [D008](decisions/D008-readiness-decision-record.md).
- **Action:** `readiness.py` adds the `readiness-decision` record, decided by the
  Business direction decider or delegate, with outcome, reason, conditions and a
  server-computed basis. "Ready to build?" now shows the current call, earlier
  calls and, for the decider, the form. The board shows the call beside the button
  and flags when the basis has changed since.
- Tests: readiness backend and UI tests added; full suites passing.

## 2026-11-23 (late evening) · branch `claude/thesis-board`

- **Decision:** C2 (horizontal trackers, short labels, readable signs, numbered
  wayfinding) is the design system for the whole experience, with light and dark
  modes; the light palette goes fluorescent (neon lime, fluorescent pink, neon teal).
  Recorded as [D007](decisions/D007-c2-tracker-design-system.md).
- **Decision:** build it on a new branch, `claude/thesis-board`, cut from
  `claude/northstar-ux`.
- **Action:** every hard-coded colour in the stylesheets became a semantic token;
  `theme.css` holds the light and dark values, Space Grotesk headings and the C2
  components. Light and dark toggle in the top bar (local preference only).
- **Action:** Project home is now the case board: 01 Mission, 02 Win conditions,
  03 Case strength, 04 Problem (Research), 05 Solution (Design), 06 Milestones, then
  07 At the table (needs, what changed, people). Areas open into a parts view; each
  part opens its existing requirement page. "Ready to build?" shows six checks and
  sends the call to Decisions & issues. Nothing new is stored.
- Tests: 797 JavaScript, 1110 Python, launcher check passing. Core loop walked in
  light and dark; desktop, tablet and phone checked.

## 2026-11-23 (evening)

- **Decision:** reframe the experience as one shared, openly running case: the
  sponsor's promise and proof at the top, Research validating the problem and
  Design validating the solution, requirement areas as tanks, Decisions & issues as
  the shared table. Readiness to build is a human decision the board informs.
  Same system underneath; only the experience changes.
- **Decision:** anything that diverges from the infrastructure (records,
  permissions, publication, decision rights, stored data) comes back to the owner
  before it is enacted.
- **Decision:** build the new experience on a new branch, `claude/thesis-board`,
  from `claude/northstar-ux`.
- **Action:** mockups of the board, a tank opened to its full story and the readiness
  decision, from the real demo data, on a design canvas. Proposed problem and
  solution grouping shown for adjustment. Flagged: recording a readiness decision
  would need a new record type.

## 2026-11-23

- **Decision:** keep this decision and action log in the repo, updated every round.
  Commit 95a0408.
- **Action:** cut over-communication. Long page intros moved behind "About this
  page"; repeated rule sentences, negative statuses and wordy empty states removed;
  Evidence trail rows shortened. Explanatory text on the heaviest screens down
  15 to 70 percent. Commit 59a61a8. Pushed.
- **Decision:** accepting an intent change updates every place that wording
  appears ([D006](decisions/D006-accepted-intent-changes-update-mirrors.md)).
- **Decision:** team knowledge is edited only by the team's lead
  ([D005](decisions/D005-knowledge-edited-by-team-lead.md)).
- **Action:** fixed the audit findings: goals save before leaving a step, stale saves
  keep typed text, Dana gets the shared project bar, Requirements status strip,
  clearer Decision log, Mark all read, compact sidebar, tab icon, "Target to be
  confirmed". Demo measures kept without invented targets. Commit 4da09ee. Pushed.
- **Action:** audit of every screen for five people at desktop and phone width,
  plus brittleness tests. No page errors or failed requests; findings ranked.

## 2026-11-22

- **Decision:** goals and success measures belong with the Core Value Statement in
  Business Intent: the promise and its proof. Downstream findings refine them
  through Decisions & issues.
- **Action:** goals editor moved into step 1; step 3 shows them read-only.
  Commit 59857c7. Pushed.
- **Decision:** the sponsor sets the initial conditions (Business Intent, then
  Context); downstream teams validate the problem and the solution through
  consequential work; Decisions & issues is the shared accountability space.
- **Action:** Context step gains a Validation plan (validate the problem, validate
  the solution) with guidance and the AI partner; readers see what the shared effort
  is validating. Commit 22b3a9f. Pushed.
- **Decision:** Context is a deliberate step two after Business Intent.
- **Action:** Context page and navigation for everyone, numbered sponsor steps,
  "Project framing" renamed Context, answers show the requirement areas they shape.
  Commit c6fce69. Pushed.
- **Action:** building blocks as collectible cards with a dossier (profile, sources,
  links, history, care). Commit f0cb418. Pushed.
- **Decision:** requirements are read-only tanks filled by any team, with a computed
  evidence level ([D004](decisions/D004-requirement-evidence-level.md)). Logic
  quality comes from open contradictions, gaps and dependencies.
- **Action:** evidence level service and tank display. Commit c319d38. Pushed.
- **Action:** step 7: remaining suggestion views, phone pass, core loop walked end to
  end in the browser. Commit ce3ed61. Pushed.
- **Decision:** anything a person works on in a workbench or Business Intent stays
  editable; AI output is only a suggestion; edit, ask the AI partner, edit again
  ([D003 rule 7](decisions/D003-suggestions-require-validation.md)).
- **Action:** shared suggestion states on AI suggestions. Commits dedb855, 5f73ac8.
- **Decision:** "AI Coach" and "Integrity Review" are called "AI partner" everywhere.
  Commits 12cf4fe, de7dc44.
- **Action:** redesign steps 1 to 6: navigation, Evidence trail and Knowledge,
  Project home, Decisions & issues, workbench and Business Intent, building blocks.
  Commits 10501c6 to e35b7b1.
- **Action:** launcher auto-reload that keeps demo data (`--reload`). Commit 7d9fac8.

## 2026-11-21

- **Decision:** keep a record of the given version and build the new design on a
  separate branch.
- **Action:** branch `claude/northstar` tagged `given-northstar` (654febf); new work
  on `claude/northstar-ux`. Crisp workspace design system replaces the previous design values.
  Commits f13bb6f, 75536d7.
