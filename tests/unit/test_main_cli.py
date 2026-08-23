from unittest.mock import MagicMock, patch

import main
from src.utils.config import Config


def _patch_pipeline_dependencies():
    """
    Patch every task/service run_elt_pipeline touches so the flow body can be
    exercised in-process with no network, database, or GCP calls.
    """
    mock_state_mgr_instance = MagicMock()
    mock_state_mgr_instance.get_watermark.return_value = None

    return patch.multiple(
        main,
        extract_connector_task=MagicMock(return_value=[]),
        load_gcs_step_task=MagicMock(return_value=[]),
        load_bigquery_step_task=MagicMock(return_value=[]),
        transform_step_task=MagicMock(return_value=None),
        commit_watermark_step_task=MagicMock(return_value=None),
        record_pipeline_metrics=MagicMock(return_value=None),
        StateManager=MagicMock(return_value=mock_state_mgr_instance),
    )


def test_omitting_tenant_slug_defaults_run_args_to_configured_tenant():
    """
    The zero-change constraint: existing `python main.py` / cron invocations
    call run_elt_pipeline without tenant_slug at all. That must still produce
    a RunArgs whose tenant_slug is the configured default ("olist-retail"),
    never None.
    """
    with _patch_pipeline_dependencies():
        main.run_elt_pipeline.fn(connector_name="postgres_db", full_refresh=True)

        assert main.extract_connector_task.call_count == 1
        _, run_args = main.extract_connector_task.call_args[0]
        assert run_args.tenant_slug == Config.DEFAULT_TENANT_SLUG
        assert run_args.tenant_slug == "olist-retail"


def test_tenant_slug_argument_propagates_into_run_args():
    """
    Passing --tenant-slug acme-coffee (threaded through as the tenant_slug
    keyword) must land on the RunArgs handed to the extract step verbatim.
    """
    with _patch_pipeline_dependencies():
        main.run_elt_pipeline.fn(
            connector_name="postgres_db",
            full_refresh=True,
            tenant_slug="acme-coffee",
        )

        assert main.extract_connector_task.call_count == 1
        _, run_args = main.extract_connector_task.call_args[0]
        assert run_args.tenant_slug == "acme-coffee"
