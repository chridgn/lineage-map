from __future__ import annotations
import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.tree import Tree
from rich import print as rprint

from .parser.dbt import load_manifest
from .parser.sql import extract_column_lineage
from .graph.builder import build_graph
from .graph.models import LineageGraph, ColumnNode

console = Console()


@click.group()
def cli() -> None:
    """LineageMap — column-level lineage for dbt projects."""


@cli.command()
@click.option(
    "--manifest",
    default="manifest.json",
    show_default=True,
    help="Path to dbt manifest.json",
)
@click.option("--port", default=3000, show_default=True, help="Port to listen on")
@click.option("--host", default="127.0.0.1", show_default=True, help="Host to bind to")
@click.option("--dialect", default=None, help="SQL dialect (snowflake, bigquery, redshift)")
def serve(manifest: str, port: int, host: str, dialect: str | None) -> None:
    """Start the LineageMap web UI at http://localhost:<port>."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed.[/red] Run: pip install 'lineagemap[server]'")
        raise SystemExit(1)

    manifest_path = Path(manifest)
    if not manifest_path.exists():
        console.print(f"[red]manifest.json not found at {manifest_path.resolve()}[/red]")
        console.print("Run [bold]dbt compile[/bold] first to generate it.")
        raise SystemExit(1)

    from .server.app import create_app
    app = create_app(manifest_path=str(manifest_path), dialect=dialect)

    console.print(f"[bold green]LineageMap[/bold green] running at [link=http://{host}:{port}]http://{host}:{port}[/link]")
    uvicorn.run(app, host=host, port=port, log_level="warning")


@cli.command()
@click.option(
    "--column", "-c",
    required=True,
    help="Column name to trace (e.g. revenue)",
)
@click.option(
    "--model", "-m",
    default=None,
    help="Model name to start from (optional; uses most downstream match if omitted)",
)
@click.option(
    "--manifest",
    default="manifest.json",
    show_default=True,
    help="Path to dbt manifest.json",
)
@click.option(
    "--dialect",
    default=None,
    help="SQL dialect (e.g. snowflake, bigquery, redshift)",
)
@click.option(
    "--json", "output_json",
    is_flag=True,
    default=False,
    help="Output raw lineage JSON instead of the tree",
)
def trace(
    column: str,
    model: str | None,
    manifest: str,
    dialect: str | None,
    output_json: bool,
) -> None:
    """Trace a column's upstream lineage through your dbt project."""
    manifest_path = Path(manifest)
    if not manifest_path.exists():
        console.print(f"[red]manifest.json not found at {manifest_path.resolve()}[/red]")
        console.print("Run [bold]dbt compile[/bold] first to generate it.")
        sys.exit(1)

    with console.status("[bold green]Loading manifest...[/bold green]"):
        dbt = load_manifest(manifest_path)

    if not dbt.models:
        console.print("[yellow]No compiled models found in manifest.[/yellow]")
        sys.exit(1)

    with console.status("[bold green]Parsing SQL...[/bold green]"):
        column_lineage: dict[str, dict[str, list[str]]] = {}
        for model_name, dbt_model in dbt.models.items():
            col_map = extract_column_lineage(dbt_model.compiled_sql, dialect=dialect)
            if col_map:
                column_lineage[model_name] = col_map

    graph = build_graph(
        models={m: dm.unique_id for m, dm in dbt.models.items()},
        column_lineage=column_lineage,
    )

    if output_json:
        click.echo(json.dumps(graph.to_dict(), indent=2))
        return

    # Find the starting node
    matches = graph.find_by_column(column)
    if not matches:
        console.print(f"[red]Column [bold]{column}[/bold] not found in any model.[/red]")
        sys.exit(1)

    if model:
        start_nodes = [n for n in matches if n.model.lower() == model.lower()]
        if not start_nodes:
            console.print(
                f"[red]Column [bold]{column}[/bold] not found in model [bold]{model}[/bold].[/red]"
            )
            console.print(f"Found in: {', '.join(n.model for n in matches)}")
            sys.exit(1)
        start_node = start_nodes[0]
    else:
        # Pick the node with the most upstream depth (most downstream in the DAG)
        start_node = _most_downstream(matches, graph)

    tree = Tree(f"[bold cyan]{start_node.column}[/bold cyan] ([dim]{start_node.model}[/dim])")
    _build_tree(start_node, graph, tree, visited=set())
    console.print(tree)


def _most_downstream(nodes: list[ColumnNode], graph: LineageGraph) -> ColumnNode:
    """Return the node with the greatest upstream depth."""
    def depth(node: ColumnNode, seen: set[str]) -> int:
        if node.id in seen:
            return 0
        seen.add(node.id)
        if not node.upstream:
            return 0
        return 1 + max(
            depth(graph.nodes[uid], seen) for uid in node.upstream if uid in graph.nodes
        )

    return max(nodes, key=lambda n: depth(n, set()))


def _build_tree(
    node: ColumnNode,
    graph: LineageGraph,
    branch: Tree,
    visited: set[str],
) -> None:
    """Recursively add upstream nodes to the Rich tree."""
    if node.id in visited:
        branch.add("[dim](cycle)[/dim]")
        return
    visited.add(node.id)

    for uid in node.upstream:
        upstream_node = graph.get_node(uid)
        if not upstream_node:
            continue
        label = f"[green]{upstream_node.column}[/green] ([dim]{upstream_node.model}[/dim])"
        child = branch.add(label)
        _build_tree(upstream_node, graph, child, visited.copy())
