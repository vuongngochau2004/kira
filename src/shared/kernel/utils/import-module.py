"""
Utility for importing Python modules with kebab-case filenames.

Python's import system doesn't support hyphens in module names.
This utility provides a way to import kebab-case Python files using
importlib.util.spec_from_file_location().

Usage in __init__.py:
    from src.shared.kernel.utils.import_module import import_kebab_module
    _module = import_kebab_module(__file__, "chat-use-case")
    ChatUseCase = _module.ChatUseCase
"""

import importlib.util
import os
import sys
from types import ModuleType
from typing import Any


def import_kebab_module(
    caller_file: str,
    module_filename: str,
    package_name: str | None = None,
) -> ModuleType:
    """Import a Python module with kebab-case filename.

    Args:
        caller_file: __file__ of the calling module (used to resolve relative paths)
        module_filename: The kebab-case filename (e.g., "chat-use-case")
        package_name: Optional fully-qualified module name for sys.modules.
                      Defaults to the filename with hyphens replaced by underscores.

    Returns:
        The imported module object

    Example:
        >>> # In src/modules/chat/application/__init__.py
        >>> from src.shared.kernel.utils.import_module import import_kebab_module
        >>> _module = import_kebab_module(__file__, "chat-use-case")
        >>> ChatUseCase = _module.ChatUseCase
    """
    # Resolve the directory of the calling module
    caller_dir = os.path.dirname(os.path.abspath(caller_file))

    # Build the full file path
    if not module_filename.endswith(".py"):
        module_filename = f"{module_filename}.py"

    file_path = os.path.join(caller_dir, module_filename)

    if not os.path.exists(file_path):
        raise ImportError(
            f"Cannot find module file: {file_path}. "
            f"Ensure the kebab-case file exists in the same directory as {caller_file}"
        )

    # Create a valid Python module name (replace hyphens with underscores)
    if package_name is None:
        package_name = module_filename.replace(".py", "").replace("-", "_")

    # If module is already loaded, return cached version
    if package_name in sys.modules:
        return sys.modules[package_name]

    # Load the module using importlib
    spec = importlib.util.spec_from_file_location(package_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create module spec for: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[package_name] = module

    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # Clean up on failure
        sys.modules.pop(package_name, None)
        raise ImportError(f"Failed to load module {file_path}: {e}") from e

    return module


def import_kebab_symbol(
    caller_file: str,
    module_filename: str,
    symbol_name: str,
    package_name: str | None = None,
) -> Any:
    """Import a specific symbol from a kebab-case Python module.

    Convenience wrapper around import_kebab_module() that returns
    a single symbol instead of the whole module.

    Args:
        caller_file: __file__ of the calling module
        module_filename: The kebab-case filename (e.g., "chat-use-case")
        symbol_name: Name of the symbol to import (e.g., "ChatUseCase")
        package_name: Optional fully-qualified module name

    Returns:
        The requested symbol from the module

    Example:
        >>> # In src/modules/chat/application/__init__.py
        >>> from src.shared.kernel.utils.import_module import import_kebab_symbol
        >>> ChatUseCase = import_kebab_symbol(__file__, "chat-use-case", "ChatUseCase")
    """
    module = import_kebab_module(caller_file, module_filename, package_name)
    if not hasattr(module, symbol_name):
        raise AttributeError(
            f"Module {module_filename} has no symbol '{symbol_name}'. "
            f"Available symbols: {[n for n in dir(module) if not n.startswith('_')]}"
        )
    return getattr(module, symbol_name)


__all__ = ["import_kebab_module", "import_kebab_symbol"]