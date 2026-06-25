from __future__ import annotations
from .models import ColumnNode, LineageGraph


def build_graph(
    models: dict[str, str],
    column_lineage: dict[str, dict[str, list[str]]],
) -> LineageGraph:
    """
    Build a LineageGraph from parsed data.

    Args:
        models: {model_name: unique_id} mapping
        column_lineage: {model_name: {output_col: ["source_table.source_col", ...]}}

    Returns:
        LineageGraph with all ColumnNodes and edges wired up.
    """
    graph = LineageGraph()

    # First pass: create all nodes
    for model_name, col_map in column_lineage.items():
        for output_col in col_map:
            node_id = _node_id(model_name, output_col)
            graph.add_node(ColumnNode(id=node_id, model=model_name, column=output_col))

    # Second pass: wire edges
    for model_name, col_map in column_lineage.items():
        for output_col, sources in col_map.items():
            node_id = _node_id(model_name, output_col)
            node = graph.get_node(node_id)
            if not node:
                continue

            for src_ref in sources:
                # src_ref is "source_table.source_column"
                parts = src_ref.rsplit(".", 1)
                if len(parts) != 2:
                    continue
                src_model, src_col = parts
                src_id = _node_id(src_model, src_col)

                # Create source node if it doesn't exist (external source tables)
                if not graph.get_node(src_id):
                    graph.add_node(ColumnNode(id=src_id, model=src_model, column=src_col))

                node.upstream.append(src_id)
                graph.nodes[src_id].downstream.append(node_id)

    return graph


def _node_id(model: str, column: str) -> str:
    return f"{model}.{column}"
