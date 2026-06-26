# Contributing to LineageMap

Thanks for your interest. Here's how to get up and running quickly.

## Setup

```bash
git clone https://github.com/christianquebral/lineagemap
cd lineagemap
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,server]"
```

## Running tests

```bash
pytest tests/
```

## Running the UI locally

```bash
# Terminal 1: backend
lineagemap serve --manifest tests/fixtures/simple_manifest.json

# Terminal 2: frontend dev server (hot reload)
cd frontend && npm install && npm run dev
```

The Vite dev server proxies `/api/*` to the FastAPI backend automatically.

## Building the frontend bundle

```bash
cd frontend && npm run build
```

This writes the production bundle to `lineagemap/server/static/` which gets served by FastAPI and shipped in the Python package.

## Good first issues

- Support `SELECT *` by resolving column lists from `schema.yml`
- Add `--output` flag to `trace` to write JSON to a file
- Add `lineagemap export` command that dumps the full graph as JSON
- Improve source table name resolution (map back to dbt source names)

## Code style

- Python 3.10+, type hints everywhere
- No comments that explain *what* the code does: only *why* when it's non-obvious
- Keep the dependency count low

## Submitting a PR

Open an issue first for anything beyond a small bug fix so we can align before you invest time. PRs without tests for new behavior will be asked to add them.
