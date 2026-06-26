from __future__ import annotations
import threading
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from ..parser.dbt import load_manifest
from ..parser.sql import extract_column_lineage
from ..graph.builder import build_graph
from ..graph.models import LineageGraph

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    manifest_path: str,
    dialect: str | None = None,
    reload_token: str | None = None,
) -> FastAPI:
    app = FastAPI(title="LineageMap", docs_url=None, redoc_url=None)

    # Mutable state — updated by /api/reload without restarting the process
    _state: dict[str, LineageGraph] = {}
    _lock = threading.Lock()

    def _load() -> LineageGraph:
        dbt = load_manifest(manifest_path)
        col_lineage = {
            name: extract_column_lineage(m.compiled_sql, dialect=dialect)
            for name, m in dbt.models.items()
        }
        return build_graph(
            models={n: m.unique_id for n, m in dbt.models.items()},
            column_lineage=col_lineage,
        )

    with _lock:
        _state["graph"] = _load()

    def _graph() -> LineageGraph:
        return _state["graph"]

    @app.get("/api/graph")
    def get_graph() -> JSONResponse:
        graph = _graph()
        nodes = []
        edges = []
        seen_edges: set[tuple[str, str]] = set()

        for node in graph.nodes.values():
            nodes.append({
                "id": node.id,
                "model": node.model,
                "column": node.column,
            })
            for uid in node.upstream:
                edge_key = (uid, node.id)
                if edge_key not in seen_edges:
                    seen_edges.add(edge_key)
                    edges.append({"source": uid, "target": node.id})

        return JSONResponse({"nodes": nodes, "edges": edges})

    @app.get("/api/search")
    def search(q: str = "") -> JSONResponse:
        q = q.strip().lower()
        if not q:
            return JSONResponse({"ids": []})
        matched = [
            n.id for n in _graph().nodes.values()
            if q in n.column.lower() or q in n.model.lower()
        ]
        return JSONResponse({"ids": matched})

    @app.post("/api/reload")
    def reload(authorization: str | None = Header(default=None)) -> JSONResponse:
        """
        Re-parse the manifest and update the in-memory graph without restarting.
        Intended for CI: after `dbt compile`, POST here to reflect the latest lineage.

        If LINEAGEMAP_RELOAD_TOKEN is set on the server, callers must supply:
            Authorization: Bearer <token>
        """
        if reload_token:
            if not authorization or authorization != f"Bearer {reload_token}":
                raise HTTPException(status_code=401, detail="Invalid or missing reload token")

        try:
            with _lock:
                new_graph = _load()
                _state["graph"] = new_graph
            return JSONResponse({
                "status": "ok",
                "nodes": len(_state["graph"].nodes),
            })
        except Exception as exc:
            return JSONResponse({"status": "error", "message": str(exc)}, status_code=500)

    # Serve built frontend
    if STATIC_DIR.exists():
        assets_dir = STATIC_DIR / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}")
        def serve_spa(full_path: str) -> FileResponse:
            return FileResponse(str(STATIC_DIR / "index.html"))
    else:
        @app.get("/")
        def no_frontend() -> JSONResponse:
            return JSONResponse(
                {"error": "Frontend not built. Run: cd frontend && npm run build"},
                status_code=503,
            )

    return app
