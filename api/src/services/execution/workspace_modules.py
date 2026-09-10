"""Workspace module cache isolation for reused execution processes."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger(__name__)


def clear_workspace_modules() -> None:
    """Evict loaded workspace modules when their cached source changed.

    If one module changed, all workspace modules are evicted because unchanged
    modules may still hold stale ``from X import Y`` references.
    """
    from src.core.module_cache_sync import get_module_sync
    from src.services.execution.virtual_import import (
        NamespacePackageLoader,
        VirtualModuleLoader,
    )

    workspace_modules = [
        (name, module)
        for name, module in sys.modules.items()
        if module is not None
        and isinstance(
            getattr(module, "__loader__", None),
            (VirtualModuleLoader, NamespacePackageLoader),
        )
    ]

    modules_to_clear: list[str] = []
    modules_kept = 0

    for name, module in workspace_modules:
        cached_hash = getattr(module, "__content_hash__", None)

        if not cached_hash:
            if isinstance(getattr(module, "__loader__", None), NamespacePackageLoader):
                continue
            modules_to_clear.append(name)
            continue

        file_path = getattr(module, "__file__", None)
        if not file_path:
            modules_to_clear.append(name)
            continue

        cached = get_module_sync(file_path)
        if not cached:
            modules_to_clear.append(name)
            continue

        loaded_storage_path = getattr(module, "__storage_path__", file_path)
        if cached.get("storage_path", cached.get("path")) != loaded_storage_path:
            modules_to_clear.append(name)
            continue

        if cached.get("hash") != cached_hash:
            modules_to_clear.append(name)
        else:
            modules_kept += 1

    if modules_to_clear:
        modules_to_clear = [name for name, _ in workspace_modules]
        modules_kept = 0

    cleared_set = set(modules_to_clear)
    for name, module in workspace_modules:
        if not isinstance(getattr(module, "__loader__", None), NamespacePackageLoader):
            continue
        prefix = name + "."
        has_surviving_child = any(
            candidate.startswith(prefix) and candidate not in cleared_set
            for candidate in sys.modules
        )
        if not has_surviving_child:
            modules_to_clear.append(name)

    for name in modules_to_clear:
        sys.modules.pop(name, None)

    if modules_to_clear or modules_kept:
        logger.debug(
            "Workspace modules: cleared=%s kept=%s%s",
            len(modules_to_clear),
            modules_kept,
            f" (cleared: {modules_to_clear})" if modules_to_clear else "",
        )
