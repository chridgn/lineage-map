from pathlib import Path
import pytest

from lineagemap.parser.sql import extract_column_lineage
from lineagemap.parser.dbt import load_manifest
from lineagemap.graph.builder import build_graph

FIXTURES = Path(__file__).parent / "fixtures"


class TestSqlParser:
    def test_simple_rename(self):
        sql = "SELECT id AS order_id, amount AS revenue FROM orders"
        result = extract_column_lineage(sql)
        assert "order_id" in result
        assert "revenue" in result
        assert any("orders" in s for s in result["order_id"])
        assert any("orders" in s for s in result["revenue"])

    def test_expression_column(self):
        sql = "SELECT first_name || ' ' || last_name AS full_name FROM customers"
        result = extract_column_lineage(sql)
        assert "full_name" in result
        sources = result["full_name"]
        assert any("first_name" in s for s in sources)
        assert any("last_name" in s for s in sources)

    def test_qualified_column(self):
        sql = (
            "SELECT o.order_id, o.revenue, c.email AS customer_email "
            "FROM stg_orders o LEFT JOIN stg_customers c ON o.customer_id = c.customer_id"
        )
        result = extract_column_lineage(sql)
        assert "order_id" in result
        assert "revenue" in result
        assert "customer_email" in result

    def test_star_is_skipped(self):
        sql = "SELECT * FROM orders"
        result = extract_column_lineage(sql)
        assert result == {}

    def test_cte(self):
        sql = """
        WITH base AS (
            SELECT id, amount FROM raw_orders
        )
        SELECT id AS order_id, amount AS revenue FROM base
        """
        result = extract_column_lineage(sql)
        assert "order_id" in result
        assert "revenue" in result

    def test_empty_on_invalid_sql(self):
        result = extract_column_lineage("NOT VALID SQL !!!")
        assert isinstance(result, dict)


class TestDbtManifest:
    def test_loads_models(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        assert "stg_orders" in manifest.models
        assert "stg_customers" in manifest.models
        assert "fct_orders" in manifest.models

    def test_loads_sources(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        assert len(manifest.sources) == 2

    def test_compiled_sql_present(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        assert "SELECT" in manifest.models["stg_orders"].compiled_sql.upper()


class TestGraphBuilder:
    def test_builds_graph(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        col_lineage = {
            name: extract_column_lineage(m.compiled_sql)
            for name, m in manifest.models.items()
        }
        graph = build_graph(
            models={n: m.unique_id for n, m in manifest.models.items()},
            column_lineage=col_lineage,
        )
        assert len(graph.nodes) > 0

    def test_find_by_column(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        col_lineage = {
            name: extract_column_lineage(m.compiled_sql)
            for name, m in manifest.models.items()
        }
        graph = build_graph(
            models={n: m.unique_id for n, m in manifest.models.items()},
            column_lineage=col_lineage,
        )
        revenue_nodes = graph.find_by_column("revenue")
        assert len(revenue_nodes) >= 1

    def test_upstream_linkage(self):
        manifest = load_manifest(FIXTURES / "simple_manifest.json")
        col_lineage = {
            name: extract_column_lineage(m.compiled_sql)
            for name, m in manifest.models.items()
        }
        graph = build_graph(
            models={n: m.unique_id for n, m in manifest.models.items()},
            column_lineage=col_lineage,
        )
        # fct_orders.revenue should trace back through stg_orders
        fct_revenue = graph.get_node("fct_orders.revenue")
        assert fct_revenue is not None
        assert len(fct_revenue.upstream) > 0
