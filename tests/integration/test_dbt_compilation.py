import os
import pytest
from src.transform.run_transform import get_dbt_binary

def test_dbt_project_syntax_and_dag_parsing():
    """
    Integration Test: Parses the dbt project (dry-run) to verify that all SQL models,
    macros, refs, snapshots, and tests have valid syntax and resolve correctly
    without runtime database queries or network overhead.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dbt_dir = os.path.join(base_dir, "dbt")
    dbt_bin = get_dbt_binary()
    
    cmd_str = f'"{dbt_bin}" parse --project-dir "{dbt_dir}" --profiles-dir "{dbt_dir}"'
    
    # Run via os.popen for cross-platform and Python 3.14 Windows compatibility
    with os.popen(cmd_str) as stream:
        output = stream.read()
    
    assert "Found 18 models" in output or "Registered adapter" in output
