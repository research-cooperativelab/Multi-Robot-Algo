"""Internal bootstrap: import main.py (at repo root) as a module.

main.py lives at the repository root alongside the searchfcr/ package directory.
Because main.py is not itself installable (it's a script with a ``__main__``
block), we import it by absolute path so there is a single source of truth
for the algorithmic code. The searchfcr wrappers then call into it.

This module exposes ``main_mod`` as the imported module object.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path


def _locate_main() -> Path:
    """Find main.py at the repo root.

    We climb up from this file until we find a ``main.py`` sibling. This keeps
    the package working both from an editable install (where the package lives
    in-tree next to main.py) and from inside test runners that cwd around.
    """
    here = Path(__file__).resolve()
    # searchfcr/_main_import.py -> searchfcr/ -> repo root
    for parent in [here.parent.parent, *here.parents]:
        candidate = parent / "main.py"
        if candidate.is_file():
            return candidate
    raise ImportError(
        "searchfcr could not locate main.py. Expected it at the repo root, "
        "one level above the searchfcr/ package directory."
    )


def _load_main():
    path = _locate_main()
    # Add the repo root to sys.path so ``import main`` works for any internal
    # relative imports inside main.py (currently there are none, but this is
    # defensive).
    repo_root = str(path.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    # If a module named 'main' is already loaded (e.g. by test collector), use
    # it as long as it looks like ours. Otherwise load fresh.
    existing = sys.modules.get("main")
    if existing is not None and getattr(existing, "__file__", None):
        try:
            if os.path.samefile(existing.__file__, str(path)):
                return existing
        except OSError:
            pass

    spec = importlib.util.spec_from_file_location("main", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["main"] = module
    spec.loader.exec_module(module)
    return module


main_mod = _load_main()

__all__ = ["main_mod"]
