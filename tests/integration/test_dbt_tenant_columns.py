import re
from pathlib import Path

import pytest

STAGING_MODELS = [
    "stg_customers.sql",
    "stg_orders.sql",
    "stg_order_items.sql",
    "stg_payments.sql",
    "stg_products.sql",
]

STAGING_DIR = Path(__file__).resolve().parents[2] / "dbt" / "models" / "staging" / "postgres"

MARTS_MODELS = [
    "dim_customers.sql",
    "dim_products.sql",
    "fct_orders.sql",
    "fct_order_items.sql",
    "fct_payments.sql",
    "wide_orders_analytics.sql",
]

MARTS_DIR = Path(__file__).resolve().parents[2] / "dbt" / "models" / "marts" / "postgres"

SNAPSHOTS_DIR = Path(__file__).resolve().parents[2] / "dbt" / "snapshots"


def assert_tenant_slug_is_projected_column(sql, model_file):
    """Verify tenant_slug appears as a projected column in a SELECT list.

    This strips dbt Jinja blocks (`{{ ... }}`), SQL block comments
    (`/* ... */`), and SQL line comments (`--`), so a `tenant_slug`
    mention only inside a comment or a Jinja config block cannot satisfy
    the check. It then inspects each remaining line individually: a line
    only counts as a projected column if, once stripped of surrounding
    whitespace and an optional single leading/trailing comma, its ENTIRE
    content is just `tenant_slug` or `<alias>.tenant_slug` (e.g.
    `o.tenant_slug,`). That tight per-line shape is what distinguishes a
    bare column reference in a SELECT projection list from a
    `tenant_slug` mention that is merely part of a JOIN predicate
    (`AND o.tenant_slug = i.tenant_slug`) or a `GROUP BY tenant_slug,
    order_id` clause: those lines carry extra tokens (`=`, another
    column, keywords) and so never match the tight pattern, even though
    they contain the substring `tenant_slug`. This function does NOT
    attempt to parse SQL structurally (no SELECT/FROM boundary
    detection) — it is a line-shape heuristic, good enough for this
    project's simply-formatted, one-column-per-line model files.

    Raises AssertionError if no line qualifies.
    """
    # Strip Jinja blocks like {{ config(...) }} or {{ ref(...) }} etc.
    no_jinja = re.sub(r"\{\{.*?\}\}", "", sql, flags=re.DOTALL)
    # Strip SQL block comments, then SQL line comments.
    no_block_comments = re.sub(r"/\*.*?\*/", "", no_jinja, flags=re.DOTALL)
    no_comments = re.sub(r"--[^\n]*", "", no_block_comments)

    projected_column_line = re.compile(r",?\s*(?:\w+\.)?tenant_slug\s*,?")
    for line in no_comments.splitlines():
        if projected_column_line.fullmatch(line.strip()):
            return
    raise AssertionError(
        f"{model_file} must select tenant_slug as a projected column, not "
        "merely reference it in a comment, JOIN predicate, or GROUP BY clause"
    )


@pytest.mark.parametrize("model_file", STAGING_MODELS)
def test_staging_model_selects_tenant_slug(model_file):
    sql = (STAGING_DIR / model_file).read_text(encoding="utf-8")
    assert_tenant_slug_is_projected_column(sql, model_file)


@pytest.mark.parametrize("model_file", MARTS_MODELS)
def test_mart_model_selects_tenant_slug(model_file):
    sql = (MARTS_DIR / model_file).read_text(encoding="utf-8")
    assert_tenant_slug_is_projected_column(sql, model_file)


@pytest.mark.parametrize("model_file", ["fct_orders.sql", "fct_order_items.sql"])
def test_incremental_facts_use_composite_tenant_key(model_file):
    sql = (MARTS_DIR / model_file).read_text(encoding="utf-8")
    composite_key_pattern = re.compile(r"unique_key\s*=\s*\[\s*['\"]tenant_slug")
    assert composite_key_pattern.search(sql), (
        f"{model_file} must include tenant_slug in its composite unique_key"
    )


def test_helper_rejects_tenant_slug_only_in_join_predicate():
    """Regression guard: a tenant-aware JOIN alone must not satisfy the check."""
    sql = """
    SELECT
        order_id,
        customer_id
    FROM orders o
    LEFT JOIN items i
        ON o.order_id = i.order_id
       AND o.tenant_slug = i.tenant_slug
    """
    with pytest.raises(AssertionError):
        assert_tenant_slug_is_projected_column(sql, "fake_model.sql")


def test_helper_rejects_tenant_slug_only_in_group_by():
    """Regression guard: a bare GROUP BY tenant_slug alone must not satisfy the check."""
    sql = """
    SELECT
        order_id,
        COUNT(*) AS n
    FROM items
    GROUP BY tenant_slug, order_id
    """
    with pytest.raises(AssertionError):
        assert_tenant_slug_is_projected_column(sql, "fake_model.sql")


def test_helper_accepts_qualified_projected_column():
    """Sanity check: an aliased projected column (e.g. o.tenant_slug,) is accepted."""
    sql = """
    SELECT
        o.tenant_slug,
        o.order_id
    FROM orders o
    """
    assert_tenant_slug_is_projected_column(sql, "fake_model.sql")


def test_snap_orders_selects_tenant_slug():
    sql = (SNAPSHOTS_DIR / "snap_orders.sql").read_text(encoding="utf-8")
    assert_tenant_slug_is_projected_column(sql, "snap_orders.sql")


def test_snap_orders_uses_composite_tenant_unique_key():
    """Regression guard for Finding 1: two tenants' identically-numbered orders
    must not collide on the snapshot key. unique_key must include tenant_slug."""
    sql = (SNAPSHOTS_DIR / "snap_orders.sql").read_text(encoding="utf-8")
    composite_key_pattern = re.compile(r"unique_key\s*=\s*\[\s*['\"]tenant_slug")
    assert composite_key_pattern.search(sql), (
        "snap_orders.sql must include tenant_slug in its composite unique_key"
    )


def test_helper_rejects_tenant_slug_only_in_comment():
    """Regression guard for the original Task 4 finding: a comment mention doesn't count."""
    sql = """{{ config(materialized='table', schema='marts') }}
    -- tenant_slug is used for tenant isolation
    SELECT
        customer_id,
        customer_city,
        customer_state
    FROM x
    """
    with pytest.raises(AssertionError):
        assert_tenant_slug_is_projected_column(sql, "fake_model.sql")
