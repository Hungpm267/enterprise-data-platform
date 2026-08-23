import subprocess
import sys


def test_tenant_slug_flag_is_documented_in_help():
    result = subprocess.run(
        [sys.executable, "main.py", "--help"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "--tenant-slug" in result.stdout
