# Adaptive Cointelligence connector capabilities

This is the implementation inventory for this repository. Including an
adapter in a package does not establish a working vendor account, compatible
remote tool contract, successful live connection or production deployment.
Credentials and private project data are not supplied.

Business reviewers should use the platform-specific review release described in
[Packaging and handoff](PACKAGING.md). Those launchers use `UnconfiguredModel`;
the developer package contains the opt-in external adapter code and settings.
Paid model calls, full-corpus processing and human simulation remain on hold.
The seeded clinic records are explicitly fictional examples, not a new evaluation
or simulation run.

## Capability matrix

| Area | What the code does | What a recipient still needs | Source |
| --- | --- | --- | --- |
| SQLite records and NetworkX graph | Persists exact record revisions, relationships and packet manifests; rebuilds a permission-scoped dependency graph. | Python 3.12+ and the packaged dependencies. This is local storage/projection, not an enterprise SQL connection or graph-server integration. | [core.py](../src/workbench/core.py), [pyproject.toml](../pyproject.toml) |
| OpenAI | Implements Responses API requests with structured output and a separate bounded PNG vision path. | A recipient-owned API key, compatible model and explicit project/general-chat assignment. A configured status is not a successful connection test or quality evaluation. | [model_provider.py](../src/workbench/model_provider.py), [model_connection.py](../src/workbench/model_connection.py) |
| Anthropic | Implements Messages API requests using a forced structured tool response. | A recipient-owned API key, compatible model and assignment. This adapter does not implement `generate_visual`; text support does not enable PDF image review. | [model_provider.py](../src/workbench/model_provider.py), [design_visual.py](../src/workbench/design_visual.py) |
| FigJam, Figma and Lucid selected-content imports | Implements bounded HTTP MCP discovery/read calls, a preview, and explicit import into a private editable submission with provenance. Defaults are FigJam `get_figjam`, Figma `get_metadata`, and Lucid `fetch` on page one. | An enabled user connection, operator-provided bearer token, vendor permission, direct file/node/document link, and read-tool arguments matching the actual server. Imports retain selected text/structure; they do not review images, live behavior, linked files or every page. | [tool_imports.py](../src/workbench/tool_imports.py), ADR 0034 (earlier decision record) |
| Figma prototype creation | Implements editable prototype staging and an explicit MCP `use_figma` write. A confirmed result must include created node and frame identities. An uncertain result is retained without automatic retry. | The Design role, a completed current working brief, released Research inputs, a saved prototype plan, staged destination, explicit confirmation, a user token, `export_enabled`, and an authorized server exposing a compatible `use_figma` contract. Preparing alternatives with a model is a separate paid operation. | [prototype_workflow.py](../src/workbench/prototype_workflow.py), [prototype_render.py](../src/workbench/prototype_render.py) |
| Jira and Azure DevOps | Prepares and locally exports exact-version payloads. A separate demo service records explicitly simulated create/update transactions and receipts in SQLite. | Live authentication, destination metadata discovery, external writes, synchronization and confirmed external receipts are not implemented. A saved endpoint or token-variable name does not activate them. | [delivery.py](../src/workbench/delivery.py), [demo_delivery.py](../src/workbench/demo_delivery.py), [receipt_delivery.py](../src/workbench/receipt_delivery.py) |
| Document ingestion and private file routing | Extracts pasted text, TXT, Markdown, CSV, JSON, DOCX, PPTX and text PDFs locally. Routes uploads to an explicitly chosen private project or conversation and retains source/version provenance. | Readable supported files: up to 5 MB, 120,000 extracted characters and 100 PDF pages. There is no XLSX parser or built-in OCR. Upload/extraction itself makes no model request and does not publish the document. | [intake_sources.py](../src/workbench/intake_sources.py), [file_uploads.py](../src/workbench/file_uploads.py), [uploads.py](../src/workbench/uploads.py) |
| Visual PDF pages | Retains private PDF originals and lazily renders exact selected pages; a requested visual review can send one to six page images with permitted context. | Poppler `pdftoppm` and `pdftotext` for rendering; a compatible vision adapter and explicit consent for AI review. The native OpenAI adapter has the image path; the Anthropic adapter currently does not. | [visual_pdf.py](../src/workbench/visual_pdf.py), [design_visual.py](../src/workbench/design_visual.py) |
| Other MCP/API definitions | Saves connection name, endpoint, purpose and an optional credential-variable name in versioned `SETTINGS-INTEGRATIONS` records. | These entries remain `not-connected`. There is no general arbitrary-endpoint discovery, authentication, tool execution or synchronization engine behind them. | [settings.py](../src/workbench/settings.py) |
| Work-tool file shortcuts | Saves validated FigJam/Figma file links and opens them in their native tool. | File access in the recipient's account. A shortcut is separate from MCP authorization, import, prototype creation and synchronization. | [project_flow.py](../src/workbench/project_flow.py) |
| Local catalog-to-catalog project copy | An operator CLI makes lossless SQLite project/history copies with provenance receipts, leaving source stores untouched. | Compatible local source catalog/files. Copies are independent, not continuing synchronization or title-based history merges; credentials, account memberships and private chat sidecars are excluded. | [project_connections.py](../src/workbench/project_connections.py) |

There is no generic enterprise SQL adapter, external graph-database connector, or
live Jira/ADO transport in this checkout. CSV extraction is text ingestion, not a
database connection. Additional connectors require their own bounded adapter and
access/provenance contract; the settings form alone does not provide one.

## Credentials and authorization

### Model connections

The developer/source launcher supports Administrator-managed model profiles and
explicit project assignments. Saving a profile makes no provider request. **Test
connection makes a small billable provider request**, without project data; it
remains held along with other paid calls. A passed text test does not establish
vision capability or semantic quality. New projects are unassigned, and requests
do not silently borrow another project's connection or fan out across providers.

Keys entered in the local Admin form are stored in a server-owned JSON file
outside project/chat records. Atomic writes use owner-only `0600` permissions on
Unix; Windows protection also depends on directory/account ACLs. This is a
plaintext local prototype secret file, not an encrypted enterprise vault. Keys
are not returned in public connection state, packets or configuration receipts.
Do not include that file or a populated managed state directory in a handoff.
See ADR 0038 (earlier decision record).

Legacy server-only environment/configuration loading still exists. The normal
model-connections startup imports it only through the explicit
`--import-server-model` or `--coach-env` path on first setup. The portable source
demo starts with no borrowed credentials. Review releases stay offline with an
unconfigured model.

### Connected tools

FigJam and Figma use the environment name `WB_FIGMA_<identity>_TOKEN`; Lucid uses
`WB_LUCID_<identity>_TOKEN`. In explicit local-role mode, the identity is the
uppercase actor, such as `SAM` or `LEE`; authenticated accounts use the server's
hashed principal identifier. Settings displays the exact variable name needed.
Only its availability is exposed, not the token value.

Connection records store the enabled flag, tool, bounded argument mapping and
protocol, not the token. Credentials must be supplied to the Workbench server by
the operator. Another tool's connector authorization and browser login cookies are
not reused. OAuth client registration, token provisioning/refresh and enterprise
SSO are not implemented here.

The MCP reader accepts only its fixed Figma/Lucid endpoints, supported protocol
identifiers and allowlisted read operations. Redirects are refused. Preview sends
the configured selection arguments, not the project brief or private discussion.
Explicit import retains origin URL, operation, arguments, retrieval time and
content digest. The separate prototype writer sends the reviewed generated
specification to its staged Figma destination only after confirmation.

## Verification boundary

The repository has offline tests for native model transports and assignments,
MCP imports, prototype write receipts, upload routing and delivery simulations.
Provider HTTP responses and MCP writers in these tests are mocked or injected;
they do not certify a live vendor connection. Relevant suites include
`test_model_connections.py`, `test_tool_imports.py`,
`test_prototype_workflow.py`, `test_file_uploads.py`, `test_demo_delivery.py` and
`test_receipt_delivery.py` under [tests](../tests/).

No live provider, MCP authorization, external delivery or semantic-quality result
is established by this inventory. Check the release verification record for the
specific platforms and workflows actually exercised. Keep private credentials,
client sources, full-corpus processing and human simulation outside the fictional
review package.
