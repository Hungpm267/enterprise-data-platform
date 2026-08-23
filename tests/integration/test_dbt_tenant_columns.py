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


@pytest.mark.parametrize("model_file", STAGING_MODELS)
def test_staging_model_selects_tenant_slug(model_file):
    sql = (STAGING_DIR / model_file).read_text(encoding="utf-8")
    assert "tenant_slug" in sql, f"{model_file} must select tenant_slug through"
