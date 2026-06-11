"""
Kernel utility functions for cross-cutting concerns.

Provides import utilities for loading kebab-case Python module files
via importlib.util.spec_from_file_location().
"""

import importlib.util
import os

# Load the kebab-case module file directly since Python imports don't support hyphens
_utils_dir = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "shared.kernel.utils.import-module",
    os.path.join(_utils_dir, "import-module.py"),
)
if _spec is None or _spec.loader is None:
    raise ImportError("Cannot create module spec for import-module.py")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

import_kebab_module = _module.import_kebab_module
import_kebab_symbol = _module.import_kebab_symbol

__all__ = ["import_kebab_module", "import_kebab_symbol"]