from __future__ import annotations
import sqlglot
from sqlglot import exp
from sqlglot.lineage import lineage as _sqlglot_lineage, Node


def extract_column_lineage(
    sql: str,
    dialect: str | None = None,
) -> dict[str, list[str]]:
    """
    Parse compiled dbt SQL and return column-level lineage.

    Returns:
        {output_column: ["source_table.source_column", ...]}

    Handles CTEs, aliases, expressions, and cross-table joins.
    SELECT * columns are skipped (no schema info available without warehouse).
    """
    try:
        ast = sqlglot.parse_one(sql, dialect=dialect, error_level=sqlglot.ErrorLevel.WARN)
    except sqlglot.errors.SqlglotError:
        return {}

    output_cols = _get_output_columns(ast)
    result: dict[str, list[str]] = {}

    for col in output_cols:
        try:
            root = _sqlglot_lineage(col, sql, dialect=dialect)
            sources = _collect_leaf_sources(root)
            result[col] = sources
        except Exception:
            result[col] = []

    return result


def _get_output_columns(ast: exp.Expression) -> list[str]:
    """Extract the named output columns from the outermost SELECT."""
    # Walk to the outermost select (skip CTEs)
    select = ast
    if isinstance(ast, exp.With):
        select = ast.this

    if not isinstance(select, exp.Select):
        return []

    columns = []
    for expr in select.selects:
        if isinstance(expr, exp.Star):
            continue  # skip SELECT *
        elif isinstance(expr, exp.Alias):
            columns.append(expr.alias)
        elif isinstance(expr, exp.Column):
            columns.append(expr.name)
        elif isinstance(expr, (exp.Anonymous, exp.Func)):
            # Function without alias — not traceable by name, skip
            pass
        else:
            # Other expressions without alias
            pass

    return columns


def _collect_leaf_sources(node: Node) -> list[str]:
    """
    Recursively walk a sqlglot lineage Node tree and collect leaf sources.
    Leaf nodes represent actual source table columns.
    """
    if not node.downstream:
        # Leaf node — extract table.column
        table_name = _source_table_name(node)
        if table_name:
            # node.name may be alias-qualified ("o.revenue") — use just the column part
            col_name = node.name.split(".")[-1]
            return [f"{table_name}.{col_name}"]
        return []

    sources: list[str] = []
    for child in node.downstream:
        sources.extend(_collect_leaf_sources(child))

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique


def _source_table_name(node: Node) -> str | None:
    """Extract table name from a leaf Node's source expression."""
    src = node.source
    if src is None:
        return None
    if isinstance(src, exp.Table):
        # Always use the actual table name, not the alias
        # (alias would give us "o" instead of "stg_orders")
        return src.name or node.source_name or None
    if isinstance(src, exp.Select):
        return node.source_name or None
    return node.source_name or None
