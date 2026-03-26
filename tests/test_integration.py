"""Integration test — runs the full test_synthetic.py pipeline via subprocess."""

import subprocess
import sys
import os

import pytest


@pytest.mark.slow
def test_full_synthetic_pipeline():
    """Run the existing test_synthetic.py as a subprocess."""
    scr_dir = os.path.join(os.path.dirname(__file__), "..", "SCR")
    result = subprocess.run(
        [sys.executable, "test_synthetic.py"],
        cwd=scr_dir,
        capture_output=True, text=True, timeout=600,
    )
    assert result.returncode == 0, (
        f"test_synthetic.py failed with exit code {result.returncode}:\n"
        f"STDERR:\n{result.stderr[-2000:]}\n"
        f"STDOUT (last 2000 chars):\n{result.stdout[-2000:]}"
    )
