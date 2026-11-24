# D014: four questions for the owner

Status: **open**. Prepared 26 November 2026 for the owner to decide. Each has a
recommendation and what it would change. Nothing here is built until answered.

| # | Question | Recommendation | Why | What changes if accepted |
|---|---|---|---|---|
| 1 | Which relations must a comparison include? | Compare every relation, but lead only with scope and version differences. | Relation and use nearly always differ between Research and Design, so they are noise as a headline. This is how System checks already displays it. | Nothing further; confirms current behaviour. |
| 2 | Should compatible differences be shown at all? | Show them, folded under "Also differs". Never count them. | Hiding them removes the trace; counting them buries real ones. | Nothing further; confirms current behaviour. |
| 3 | Who resolves a difference between two groups? | The lead of the group that **widened** the scope answers first (confirm, narrow or supply evidence). If the two leads disagree, it becomes an issue in Decisions & Issues and the requirement owner decides, or the sponsor when intent is affected. | The widening team holds the burden of support. Existing decision rights already cover the escalation. | A "respond" action on each difference for the widening team's lead, and a one-click "raise as issue". Today nobody is assigned. |
| 4 | Is version skew a conflict or a lighter "needs review"? | "Needs review", shown in the lead line, never a conflict by itself. It becomes a concern only when the newer version changed the evidence rating or the wording relied on. | Most skew is harmless lag. Treating all of it as conflict would train people to ignore System checks. | Skew wording changes to "review the newer version"; a flag when the newer version lowered its rating. |

## Also for the owner (from the core-loop walk)

- **Practitioner review of the recipes.** The component recipes and category needs
  are a first draft. The researcher whiteboard has a section for marking them up.
- **A challenge lowers coverage to Low** for the whole requirement while it is open
  (existing rule). With System checks now reporting differences without raising
  issues, that rule only applies when someone chooses to raise one. Keep as is, or
  let a scoped challenge lower coverage only for the scope it disputes?
