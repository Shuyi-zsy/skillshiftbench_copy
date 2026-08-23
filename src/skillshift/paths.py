"""Filesystem locations of the shipped data files.

Resolved relative to the installed package so that an editable install, a wheel
install and a source checkout all find the same files.
"""

from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = PACKAGE_ROOT / "schemas"

# `data/` lives next to `src/`, not inside the package: it is benchmark content
# rather than code, and it is large enough that shipping it inside every wheel
# would be wasteful.  An editable install (the documented workflow) sees it at
# the repository root.
REPO_ROOT = PACKAGE_ROOT.parents[1]
DATA_DIR = REPO_ROOT / "data"
TASKS_DIR = DATA_DIR / "tasks"
ID_MAP_PATH = TASKS_DIR / "id_map.csv"
CALIBRATION_SET_PATH = DATA_DIR / "calibration_set.json"
REFERENCE_RESULTS_DIR = DATA_DIR / "reference_results"
