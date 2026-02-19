"""Dynamic loader for scripts/init.py from the template."""

from __future__ import annotations

import importlib.util
import os
import sys
import traceback
from pathlib import Path
from types import ModuleType


def load_init_module(template_dir: Path) -> ModuleType:
    """Load ``scripts/init.py`` as a Python module.

    Uses ``importlib.util`` to load the file without requiring
    ``uv run --script``, which avoids a subprocess call.

    Args:
        template_dir: Root of the extracted template.

    Returns:
        The loaded module.

    Raises:
        FileNotFoundError: If ``scripts/init.py`` does not exist.
    """
    init_py = template_dir / 'scripts' / 'init.py'
    if not init_py.exists():
        msg = f'scripts/init.py not found in {template_dir}'
        raise FileNotFoundError(msg)

    spec = importlib.util.spec_from_file_location(
        '_template_init', str(init_py)
    )
    if spec is None or spec.loader is None:  # pragma: no cover
        msg = f'Could not load {init_py}'
        raise ImportError(msg)

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_init(
    template_dir: Path,
    config_kwargs: dict,
    *,
    init_mod: ModuleType | None = None,
) -> bool:
    """Load init.py and run init_project with the given config.

    Args:
        template_dir: Root of the extracted template.
        config_kwargs: Keyword arguments for ``ProjectConfig``.
        init_mod: Pre-loaded init module (skips ``load_init_module``).

    Returns:
        True on success, False on failure.
    """
    mod = init_mod or load_init_module(template_dir)
    config = mod.ProjectConfig(**config_kwargs)
    try:
        return mod.init_project(config, template_dir)
    except Exception as exc:
        print(f'error: {exc}', file=sys.stderr)  # noqa: T201
        if os.environ.get('PYPKGKIT_DEBUG'):
            traceback.print_exc(file=sys.stderr)
        return False
