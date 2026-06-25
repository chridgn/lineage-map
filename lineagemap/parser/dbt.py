from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass


@dataclass
class DbtModel:
    unique_id: str
    name: str
    compiled_sql: str
    depends_on: list[str]   # list of upstream unique_ids


@dataclass
class DbtSource:
    unique_id: str
    name: str
    source_name: str


@dataclass
class DbtManifest:
    models: dict[str, DbtModel]    # name → DbtModel
    sources: dict[str, DbtSource]  # name → DbtSource


def load_manifest(path: str | Path) -> DbtManifest:
    """
    Load and parse a dbt manifest.json file.
    Supports dbt v1.0–1.7 (compiled_sql and compiled_code field names).
    """
    data = json.loads(Path(path).read_text())

    models: dict[str, DbtModel] = {}
    sources: dict[str, DbtSource] = {}

    for uid, node in data.get("nodes", {}).items():
        if node.get("resource_type") != "model":
            continue

        # dbt ≥1.4 renamed compiled_sql → compiled_code
        compiled = node.get("compiled_code") or node.get("compiled_sql") or ""
        if not compiled:
            continue

        models[node["name"]] = DbtModel(
            unique_id=uid,
            name=node["name"],
            compiled_sql=compiled,
            depends_on=node.get("depends_on", {}).get("nodes", []),
        )

    for uid, src in data.get("sources", {}).items():
        name = src.get("name", "")
        source_name = src.get("source_name", "")
        full_name = f"{source_name}.{name}" if source_name else name
        sources[full_name] = DbtSource(
            unique_id=uid,
            name=name,
            source_name=source_name,
        )

    return DbtManifest(models=models, sources=sources)
