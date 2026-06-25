# LineageMap

Column-level data lineage for dbt projects. One command, no catalog required! Super lightweight and easy to use.

```
$ lineagemap trace --column revenue

revenue (fct_orders)
└── revenue (stg_orders)
    └── amount (raw.orders)
```

## Install

```bash
pip install lineagemap
```

## Usage

Run `dbt compile` first, then point LineageMap at your `manifest.json`:

```bash
# Trace a column upstream through all models
lineagemap trace --column revenue

# Scope to a specific model
lineagemap trace --column revenue --model fct_orders

# Export full lineage graph as JSON
lineagemap trace --column revenue --json

# Specify SQL dialect
lineagemap trace --column revenue --dialect snowflake

# Use a manifest at a non-default path
lineagemap trace --column revenue --manifest path/to/manifest.json
```

## How it works

1. Reads `manifest.json` (the compiled output of `dbt compile`) — no live warehouse connection needed
2. Parses each model's compiled SQL using [sqlglot](https://github.com/tobymao/sqlglot) to extract column-level dependencies
3. Builds a column lineage graph and lets you trace any column upstream

## Status

- [x] Phase 1 — CLI + SQL parser
- [ ] Phase 2 — Local web UI with interactive DAG visualization
- [ ] Phase 3 — OSS launch + hosted tier (upload manifest, shareable URL)

## Requirements

Python 3.10+, a dbt project with a compiled `manifest.json`.
