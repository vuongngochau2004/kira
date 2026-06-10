#!/usr/bin/env python3
"""Architecture validation for modular monolith migration."""
import ast
import sys
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set, Tuple


class DependencyAnalyzer:
    """Analyze module dependencies."""

    def __init__(self, root_dir: Path = Path("src")):
        self.root_dir = root_dir
        self.imports = defaultdict(set)  # module -> set of imported modules
        self.circular_deps = []
        self.layer_violations = []

    def analyze_file(self, file_path: Path) -> Dict[str, Set[str]]:
        """Extract imports from Python file."""
        imports = {"absolute": set(), "relative": set()}

        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except Exception as e:
            print(f"⚠️  Cannot parse {file_path}: {e}")
            return imports

        for node in ast.walk(tree):
            # from X import Y
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    if node.module.startswith("src."):
                        imports["absolute"].add(node.module)
                    else:
                        imports["relative"].add(node.module)
            # import X
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("src."):
                        imports["absolute"].add(alias.name)

        return imports

    def analyze_all(self):
        """Analyze all Python files."""
        for py_file in self.root_dir.rglob("*.py"):
            module_path = py_file.relative_to(self.root_dir)
            module_name = ".".join(module_path.parts[:-1]) if module_path.parent != Path(".") else "root"

            imports = self.analyze_file(py_file)
            self.imports[module_name] = imports["absolute"]

    def detect_circular(self) -> List[Tuple[str, str]]:
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        circular = []

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycle_start = path.index(node)
                circular.append(tuple(path[cycle_start:] + [node]))
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.imports.get(node, set()):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for module in self.imports:
            dfs(module, [])

        return circular

    def validate_layer_boundaries(self):
        """Validate 4-layer architecture boundaries."""
        # Define layer membership
        layer_map = {
            "api": ["serving"],
            "agents": ["agent_tools"],
            "tools": ["agent_tools"],
            "handlers": ["agent_tools"],
            "classification": ["agent_tools"],
            "retrieval": ["retrieval"],
            "indexing": ["retrieval"],
            "ingestion": ["ingestion"],
            "interfaces": ["abstractions"],
            "di": ["abstractions"],
            "database": ["storage"],
            "models": ["storage"],
            "auth": ["storage"],
            "constants": ["storage"],
            "monitoring": ["storage"],
            "evaluation": ["storage"],
            "graphs": ["agent_tools"],
        }

        # Define allowed dependencies (layer -> can depend on)
        allowed_deps = {
            "serving": ["agent_tools", "retrieval", "ingestion", "abstractions", "storage"],
            "agent_tools": ["retrieval", "ingestion", "abstractions", "storage"],
            "retrieval": ["ingestion", "abstractions", "storage"],
            "ingestion": ["abstractions", "storage"],
            "abstractions": ["storage"],
            "storage": [],
        }

        violations = []

        for module, imports in self.imports.items():
            # Determine source layer
            src_layer = None
            for prefix, layer in layer_map.items():
                if module.startswith(prefix):
                    src_layer = layer
                    break

            if not src_layer:
                continue

            # Check each import
            for imp in imports:
                imp_layer = None
                for prefix, layer in layer_map.items():
                    if imp.startswith(f"src.{prefix}"):
                        imp_layer = layer
                        break

                if not imp_layer:
                    continue

                # Check if dependency is allowed
                allowed = allowed_deps.get(src_layer, [])
                if imp_layer not in allowed and imp_layer != src_layer:
                    violations.append({
                        "module": module,
                        "layer": src_layer,
                        "imports": imp,
                        "target_layer": imp_layer
                    })

        return violations


def validate_no_circular_dependencies():
    """Validate no circular dependencies exist."""
    print("\n" + "=" * 80)
    print("🔍 CIRCULAR DEPENDENCY CHECK")
    print("=" * 80)

    analyzer = DependencyAnalyzer()
    analyzer.analyze_all()

    circular = analyzer.detect_circular()

    if circular:
        print(f"\n❌ FOUND {len(circular)} CIRCULAR DEPENDENCIES:\n")
        for i, cycle in enumerate(circular, 1):
            print(f"  {i}. {' → '.join(cycle)}")
        return False
    else:
        print("\n✅ No circular dependencies detected")
        return True


def validate_module_boundaries():
    """Validate module layer boundaries."""
    print("\n" + "=" * 80)
    print("🏗️  LAYER BOUNDARY VALIDATION")
    print("=" * 80)

    analyzer = DependencyAnalyzer()
    analyzer.analyze_all()

    violations = analyzer.validate_layer_boundaries()

    if violations:
        print(f"\n❌ FOUND {len(violations)} LAYER VIOLATIONS:\n")
        for v in violations[:20]:  # Show first 20
            print(f"  📄 {v['module']} ({v['layer']})")
            print(f"     imports {v['imports']} ({v['target_layer']})")

        if len(violations) > 20:
            print(f"\n  ... and {len(violations) - 20} more violations")
        return False
    else:
        print("\n✅ All layer boundaries respected")
        return True


def validate_dependency_rules():
    """Validate specific dependency rules."""
    print("\n" + "=" * 80)
    print("📜 DEPENDENCY RULE VALIDATION")
    print("=" * 80)

    # Rule 1: No src.protocols imports (should use src.interfaces)
    print("\n🔍 Rule 1: No src.protocols imports")

    protocol_imports = []
    for py_file in Path("src").rglob("*.py"):
        content = py_file.read_text()
        if "from src.protocols" in content or "import src.protocols" in content:
            protocol_imports.append(str(py_file.relative_to("src")))

    if protocol_imports:
        print(f"❌ FOUND {len(protocol_imports)} PROTOCOL IMPORTS:")
        for f in protocol_imports[:10]:
            print(f"  📄 {f}")
        return False
    else:
        print("✅ No src.protocols imports found")

    # Rule 2: interfaces/ should not import from concrete modules
    print("\n🔍 Rule 2: interfaces/ should be abstract")

    interface_imports = []
    for py_file in Path("src/interfaces").rglob("*.py"):
        content = py_file.read_text()
        for imp in ["src.handlers", "src.classification", "src.retrieval", "src.ingestion"]:
            if f"from {imp}" in content or f"import {imp}" in content:
                interface_imports.append((str(py_file.relative_to("src")), imp))

    if interface_imports:
        print(f"❌ FOUND {len(interface_imports)} CONCRETE IMPORTS IN INTERFACES:")
        for f, imp in interface_imports:
            print(f"  📄 {f} imports {imp}")
        return False
    else:
        print("✅ interfaces/ is properly abstract")

    return True


if __name__ == "__main__":
    results = {
        "circular": validate_no_circular_dependencies(),
        "boundaries": validate_module_boundaries(),
        "rules": validate_dependency_rules(),
    }

    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY")
    print("=" * 80)

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")

    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
