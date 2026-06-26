LineageMap — Project Spec


Column-level data lineage for dbt projects. OSS-first, zero config, self-hostable.




What this is

A solo portfolio project that may become a product. The goal is a lightweight, self-hosted tool that answers "where does this column come from?" and "what breaks if I change it?" — without requiring an enterprise data catalog.

Target user: data engineers and analytics engineers using dbt with Snowflake, BigQuery, or Redshift.

Distribution model: open source core (GitHub) → hosted tier (upload manifest, get shareable URL) → potential SaaS later.


Competitive context

The landscape has two ends with nothing in the middle:


Enterprise catalogs (Atlan, Collibra, MANTA): $40k+/yr, complex setup, overkill for small-mid teams
Open source (DataHub, OpenMetadata): powerful but require Kubernetes, Kafka, significant engineering to self-host
dbt-native: dbt Cloud has basic lineage but no column-level tracing, no impact analysis


Gap LineageMap fills: drop-in column-level lineage that works in one command, for teams that can't afford or don't want a catalog.

Closest competitor to watch: Grai — similar DevOps-style approach, small community, limited integrations.


MVP Scope

Phase 1 — Core parser + CLI (~4–6 weeks)

Build:


SQL parser using sqlglot that extracts column-level lineage from dbt model .sql files
dbt project reader that walks manifest.json and schema.yml
CLI command: lineagemap trace --column <name> → prints lineage tree in terminal
JSON export of full lineage graph


Key constraint: use manifest.json as the source of truth, not a live warehouse connection. This avoids credential handling and gives you everything you need.

Milestone: lineagemap trace --column revenue prints a full upstream tree from a real dbt project.


Phase 2 — Local web UI (~3–4 weeks)

Build:


lineagemap serve → starts localhost:3000
Interactive DAG visualization of column lineage (React + d3)
Click a column → upstream sources and downstream consumers highlight
Hover a source column → every downstream report that depends on it turns red (impact analysis)
Column and table search


The "wow" moment to design around: user hovers a source column and sees every downstream consumer light up red. That screenshot is what gets shared in dbt Slack. Make this interaction as fast and beautiful as possible.

Milestone: someone can open any dbt project, run one command, and visually explore full column-level lineage.


Phase 3 — OSS launch + hosted tier (~2–3 weeks)

Build:


Publish to GitHub with strong README, demo GIF, and install guide
Hosted version: upload manifest.json → get a shareable, read-only lineage URL (no infra required for user)
GitHub Action that auto-updates lineage on dbt project changes (CI integration = stickiness)


Launch channels: r/dataengineering, dbt Slack (#tools-and-integrations), HN Show HN, LinkedIn. No cold outreach needed — OSS tools spread through communities.

Milestone: public GitHub repo, working hosted demo, first external users.


What to cut from v1

CutReasonSpark / Airflow lineageToo much infra to support; dbt alone validates the conceptLive warehouse connectionmanifest.json has everything; credentials add complexity and riskMulti-user auth / teamsDesign for real users once you have themBI tool lineage (Tableau, Looker)Complex to parse, low ROI for MVPSlack / PagerDuty alertingAdd when users ask for itRedshift / BigQuery warehouse-specific parsingStart Snowflake-only if needed to scope further


Tech stack

LayerChoiceWhyCLI + parsingPythonEcosystem fit; data engineers are comfortable with itSQL parsersqlglotHandles CTEs, nested subqueries, SELECT *; actively maintained OSSLocal serverFastAPILightweight, fast to buildDAG visualizationReact + d3Full control over the graph renderingHosted deploymentFly.ioCheap, simple, good DXCI integrationGitHub ActionsWhere dbt teams already run their pipelines


Key implementation notes

SQL parsing approach

sqlglot parses a SQL string into an AST. Walk the AST to extract:


Which columns are selected (output)
Which tables/columns they reference (input)
CTE definitions (treat as intermediate nodes)


Example flow:

dbt model SQL → sqlglot AST → column mapping dict → lineage graph node

For SELECT a.revenue + b.fx_rate AS adjusted_revenue FROM orders a JOIN fx b ON ...:


Output column: adjusted_revenue
Input columns: orders.revenue, fx.fx_rate


manifest.json structure

dbt's compiled manifest.json contains:


nodes: every model, test, and source with compiled SQL
sources: raw source tables
parent_map / child_map: table-level dependency graph


Use the compiled SQL from nodes[*].compiled_sql for parsing — it has CTEs resolved and refs substituted.

Graph data model

python@dataclass
class ColumnNode:
    id: str           # "model.project.orders.revenue"
    model: str        # "orders"
    column: str       # "revenue"
    upstream: list[str]   # list of ColumnNode ids
    downstream: list[str] # list of ColumnNode ids

Store as adjacency list. Export to JSON for the frontend.

DAG visualization

Use d3-dag or dagre-d3 for layout (handles DAG layout automatically — don't hand-roll this). React renders the SVG. Key interactions:


Click node → highlight connected subgraph (upstream = blue, downstream = red)
Hover node → show tooltip with model name, column type, test coverage
Search box filters to matching nodes and zooms



Folder structure (suggested)

lineagemap/
├── lineagemap/
│   ├── __init__.py
│   ├── cli.py            # Click CLI entrypoint
│   ├── parser/
│   │   ├── sql.py        # sqlglot-based column extractor
│   │   └── dbt.py        # manifest.json reader
│   ├── graph/
│   │   ├── builder.py    # builds ColumnNode graph from parsed data
│   │   └── models.py     # dataclasses
│   └── server/
│       ├── app.py        # FastAPI app
│       └── routes.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── Graph.jsx     # d3 DAG component
│   │   └── Search.jsx
│   └── package.json
├── tests/
│   ├── fixtures/         # sample dbt manifests for testing
│   └── test_parser.py
├── README.md
├── pyproject.toml
└── .github/
    └── workflows/
        └── lineagemap.yml  # GitHub Action


README structure (for launch)

A strong README is your primary marketing. Structure:


One-line description — "Column-level lineage for dbt. One command, no catalog required."
Demo GIF — record the "hover to see impact" interaction. This is the hook.
Install — pip install lineagemap then lineagemap serve
How it works — brief: reads manifest.json, parses SQL, builds graph
Comparison table — vs DataHub, vs Atlan, vs dbt Cloud native lineage
Roadmap — shows it's alive and going somewhere
Contributing — lower the bar for first PRs



Portfolio framing

When describing this project in interviews or a portfolio:


"Built LineageMap, an open source column-level data lineage tool for dbt projects. It parses compiled SQL using sqlglot to construct a full column dependency graph, exposed via a local DAG visualization and a one-command CLI. Designed to fill the gap between no lineage visibility and expensive enterprise catalogs."



Skills it demonstrates: data platform architecture, SQL parsing/AST traversal, graph data structures, developer tooling, OSS project management.


What success looks like

PhaseSignalPhase 1 doneYou can trace revenue through your own dbt project end-to-endPhase 2 doneYou'd use this yourself every weekPhase 3 doneSomeone you don't know opens a GitHub issueProduct signalSomeone asks if there's a paid hosted version


Open questions to revisit


Should v1 support Snowflake-specific SQL syntax edge cases, or rely on sqlglot's dialect handling?
Hosting: Fly.io vs Railway vs Render for the hosted tier?
License: MIT (max adoption) vs BSL (protects hosted tier) — decide before launch
Should the GitHub Action commit updated lineage JSON to the repo, or post to the hosted service?