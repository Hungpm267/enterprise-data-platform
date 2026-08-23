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


def assert_tenant_slug_is_projected_column(sql, model_file):
    """Verify tenant_slug appears as a projected column in a SELECT list.

    This strips SQL line comments (`--`) and dbt Jinja config/depends_on
    blocks so that a `tenant_slug` mention only inside a comment (or inside
    a `{{ config(...) }}` block, or in a `FROM`/`JOIN` clause) does not
    satisfy the assertion. It then requires `tenant_slug` to be immediately
    followed by a comma or a newline (allowing trailing whitespace), which
    is the shape of a bare column reference in a SELECT projection list.
    """
    # Strip Jinja blocks like {{ config(...) }} or {{ ref(...) }} etc.
    no_jinja = re.sub(r"\{\{.*?\}\}", "", sql, flags=re.DOTALL)
    # Strip SQL line comments.
    no_comments = re.sub(r"--[^\n]*", "", no_jinja)

    pattern = re.compile(r"\btenant_slug\b[ \t]*(,|\r?\n)")
    assert pattern.search(no_comments), (
        f"{model_file} must select tenant_slug as a projected column, "
        "not merely reference it in a comment or non-projection clause"
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
    assert "unique_key=['tenant_slug'" in sql.replace('"', "'"), (
        f"{model_file} must include tenant_slug in its composite unique_key"
    )
