"""Structure rules for the kira package (see CLAUDE.md "Architecture Rules").

These are cheap static checks: they read source files, they do not import them.
"""

import ast
import re
from pathlib import Path

KIRA = Path(__file__).resolve().parents[2] / "kira"
TESTS_UNIT = Path(__file__).resolve().parent

# Modules allowed to pull objects from kira.deps: HTTP/task/CLI entry points.
DEPS_CONSUMERS = {"main.py", "router.py", "sse.py", "dependencies.py", "tasks.py", "cli.py"}
DEPS_CONSUMER_FILES = {"pipeline_lab/service.py"}  # admin tool that inspects the live chain

# Interfaces (ABC/Protocol) are only for things with several implementations.
INTERFACE_FILES = {
    "providers/llm/base.py",
    "providers/embedding/base.py",
    "chat/intent/base.py",
    "chat/handlers/base.py",
    "legal/ports.py",
    "legal/graph/base.py",
}


def _sources() -> list[Path]:
    return [
        p
        for p in KIRA.rglob("*.py")
        if "__pycache__" not in p.parts and "migrations" not in p.parts
    ]


def _imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{a.name}" for a in node.names)
        elif isinstance(node, ast.Import):
            modules.update(a.name for a in node.names)
    return modules


def _rel(path: Path) -> str:
    return path.relative_to(KIRA).as_posix()


def test_routers_are_only_imported_by_main() -> None:
    offenders = [
        _rel(p)
        for p in _sources()
        if p.name != "main.py"
        and any(m.startswith("kira.") and m.endswith(".router") for m in _imported_modules(p))
    ]
    assert offenders == []


def test_routers_do_not_run_sql() -> None:
    offenders = []
    for p in KIRA.rglob("router.py"):
        text = p.read_text()
        if re.search(r"\bselect\(|\b(db|session)\.execute\(|^from sqlalchemy import", text, re.M):
            offenders.append(_rel(p))
    assert offenders == [], "move queries into the feature's repository.py"


def test_only_entry_points_use_the_wiring_module() -> None:
    offenders = [
        _rel(p)
        for p in _sources()
        if p.name != "deps.py"
        and p.name not in DEPS_CONSUMERS
        and _rel(p) not in DEPS_CONSUMER_FILES
        and any(m == "kira.deps" or m.startswith("kira.deps.") for m in _imported_modules(p))
    ]
    assert offenders == [], "services receive their dependencies; only entry points read kira.deps"


def test_interfaces_live_in_known_places() -> None:
    offenders = []
    for p in _sources():
        tree = ast.parse(p.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = {ast.unparse(b) for b in node.bases}
                if bases & {"ABC", "Protocol"} and _rel(p) not in INTERFACE_FILES:
                    offenders.append(f"{_rel(p)}::{node.name}")
    assert offenders == [], "add an interface only when there are two real implementations"


def test_unit_tests_mirror_the_package_tree() -> None:
    offenders = [
        d.relative_to(TESTS_UNIT).as_posix()
        for d in TESTS_UNIT.rglob("*")
        if d.is_dir()
        and "__pycache__" not in d.parts
        and not (KIRA / d.relative_to(TESTS_UNIT)).is_dir()
    ]
    assert offenders == [], "tests/unit/<x>/ must match kira/<x>/"
