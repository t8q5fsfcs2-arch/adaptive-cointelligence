# D009: Governed meaning across domains and the enterprise

Status: accepted by the user, 24 November 2026. Built in steps on `claude/thesis-board`.
This extends the scope line in `CLAUDE.md` ("no enterprise graph infrastructure
without explicit approval"): the user approved an enterprise meaning layer. Storage
stays SQLite. No graph database, no embeddings.

## What was approved

1. **Enterprise store.** One store beside the project catalog holds enterprise
   concepts, mappings and meaning decisions as versioned records. Projects
   reference an enterprise concept at an exact version; adopting a newer version
   is a deliberate, recorded step. Project and private material never flows up
   automatically.
2. **Two roles, assigned by an administrator.** Semantic services proposes and
   facilitates and never decides. The enterprise steward decides only what goes
   beyond one domain. Domain leads decide inside their domain (D005 unchanged).
3. **People first.** Semantic services is a team using this interface. An external
   system connecting through an API would be a separate decision.
4. **Data model.** Boundaries on each concept (includes, excludes, not to be
   confused with, permitted domains); a reach level (project, domain, named
   domains, enterprise); typed mappings (same-as, broader, narrower, related,
   distinct-from) that are proposed and approved, never inferred; meaning proposals
   and decisions as records with reason, decider and exact basis.

## Rules that hold throughout

- Widening reach is always a proposal and a decision, never an edit.
- AI may suggest alignments (D003: visibly suggested, editable, counted only when
  validated). It never approves a mapping or changes reach.
- Earlier versions of a concept and the reasons for each change are kept.

## Steps

1. **Built:** boundaries (includes, excludes, not to be confused with) and reach on
   a team's terms and categories. The fields are optional, so knowledge saved
   earlier keeps its exact content and reads as project reach. A lead can set
   project or domain reach; wider values are refused until proposals exist. Active
   boundaries are included in the guidance the team's AI partner receives.
2. **Built:** `meaning-proposal` records. A team member proposes a typed mapping
   between two teams' concepts, or sharing a concept with another team. The lead
   of each team it touches decides explicitly, with a reason; a mapping needs both
   leads, a share needs the owning lead. One decline closes it. A proposal keeps
   the exact wording it was based on; a concept that changed since cannot be
   approved on the old basis. The proposer can withdraw; a lead can retire an
   approved one. Approved mappings and shares are a projection over these
   records; team knowledge is not rewritten. **Not yet:** approved mappings and
   shared concepts are shown to people but are not supplied to another team's AI
   partner. That changes what a team's AI receives and its recorded basis, so it
   needs its own decision.
3. **Built:** the enterprise store (`<site>-enterprise.sqlite3`, beside the project
   catalog) with three record types: `enterprise-roles`, `enterprise-proposal`
   and `enterprise-concept`. An administrator assigns Semantic services and
   enterprise stewards; nobody holds both. Semantic services or a team's lead
   proposes wider reach for an active concept in a project they can open. The
   team lead and a steward both decide, as two different people; Semantic
   services cannot decide. Approval copies the exact wording into an enterprise
   concept version; a concept edited since the proposal cannot be approved. A
   steward can retire an enterprise concept. Project stores are only read. The
   Enterprise context page (administrators and the two roles) shows counts per
   team, proposals, enterprise concepts, reach and roles; it does not show
   concept wording from projects.
   **Adoption, built:** a team's lead adopts an enterprise concept at an exact
   version. The adoption is an `enterprise-adoption` record in the project's own
   store with the full wording, so nothing in a project changes when a newer
   enterprise version appears; the lead reviews old and new wording side by side
   and moves deliberately, or drops it. The server resolves the concept from the
   enterprise store and discards anything the browser sends in its place. A concept
   with named reach can be adopted only by a team with a matching name. The
   Enterprise context page shows where each concept is in use and which teams are
   behind.
   **Not yet:** AI-use counts on the overview; supplying adopted concepts to a
   team's AI partner (same open decision as step 2).
4. **Built:** facilitated sessions (`enterprise-session` records in the enterprise
   store). Semantic services starts a session for one team in a project it can
   open, and keeps an agenda of discussion topics and that team's open proposals.
   A linked item takes its state only from the proposal: the facilitator can add,
   order, remove and annotate items and mark a topic discussed, and cannot move a
   proposal. Deciders can decide from the session. Closing needs a summary; every
   agenda change is a new version. The wording behind a mapping between a
   project's teams is shown only to that project's members. No AI suggestion is
   shown in a session; that needs a live model connection and its own design.
