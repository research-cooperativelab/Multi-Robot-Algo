"""Shared test configuration.

Ensures the repo root is on ``sys.path`` so ``import searchfcr`` works when
tests are run without a prior ``pip install -e .``.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
