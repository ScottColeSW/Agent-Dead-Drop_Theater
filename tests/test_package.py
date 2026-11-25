import tomllib
from pathlib import Path

import deaddrop

ROOT = Path(__file__).resolve().parent.parent


def test_version_matches_pyproject():
    with open(ROOT / "pyproject.toml", "rb") as handle:
        project = tomllib.load(handle)["project"]
    assert deaddrop.__version__ == project["version"]
