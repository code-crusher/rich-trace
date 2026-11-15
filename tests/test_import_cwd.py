import os
import subprocess
import sys
from textwrap import dedent

import pytest


@pytest.mark.parametrize(
    "error",
    [
        "FileNotFoundError",
        "PermissionError",
        "OSError",
    ],
)
def test_import_with_unavailable_cwd(error: str) -> None:
    """Importing rich should succeed when ``os.getcwd()`` raises an OSError."""
    script = dedent(
        f"""\
        import os
        from unittest.mock import patch

        def _raise(errno=1, message="Operation not permitted"):
            raise {error}(errno, message)

        with patch.object(os, "getcwd", side_effect=_raise):
            import rich

        assert rich._IMPORT_CWD == ""
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        cwd=os.getcwd(),
    )
    assert result.returncode == 0, result.stderr