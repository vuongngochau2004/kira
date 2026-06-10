#!/usr/bin/env python3
"""Comprehensive dependency analysis for modular monolith migration."""
import ast
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Set


class DependencyMapper:
    """Map and visualize module dependencies."""

    def __init__(self, root_dir: Path = Path("src")):
        self.root_dir = root_dir
        self.dependencies = defaultdict(lambda: {"in": set(), "out": set()})
        self.module_files = defaultdict(list)

    def extract_imports(self, file_path: Path) -> Set[str]:
        """Extract internal imports from file (imports from other src modules)."""
        imports = set()

        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except:
            return imports

        # List of known internal modules in src/
        internal_modules = {
            "agents", "api", "auth", "classification", "config", "constants",
            "database", "di", "evaluation", "graphs", "handlers", "indexing",
            "ingestion", "interfaces", "main", "models", "monitoring", "retrieval",
            "tools"
        }

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    # Check if it's an internal import
                    first_part = node.module.split(".")[0]
                    if first_part in internal_modules:
                        imports.add(node.module)

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    first_part = alias.name.split(".")[0]
                    if first_part in internal_modules:
                        imports.add(alias.name)

        return imports

    def map_all(self):
        """Map all dependencies in src/."""
        for py_file in self.root_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue

            # Get relative path from root_dir
            rel_path = py_file.relative_to(self.root_dir)

            # Extract module name (directory path, not including filename)
            if rel_path.parent != Path("."):
                module = ".".join(rel_path.parts[:-1])
            else:
                # File is directly in src/ root (e.g., src/main.py)
                module = "root"

            self.module_files[module].append(str(py_file))

            imports = self.extract_imports(py_file)
            for imp in imports:
                imp_module = ".".join(imp.split(".")[1:])  # Remove "src."
                self.dependencies[module]["out"].add(imp_module)
                self.dependencies[imp_module]["in"].add(module)

    def generate_graph(self) -> Dict:
        """Generate dependency graph for visualization."""
        nodes = []
        edges = []

        for module, deps in self.dependencies.items():
            nodes.append({
                "id": module,
                "files": len(self.module_files[module]),
                "in_degree": len(deps["in"]),
                "out_degree": len(deps["out"])
            })

            for dep in deps["out"]:
                edges.append({"from": module, "to": dep})

        return {"nodes": nodes, "edges": edges}

    def find_critical_nodes(self) -> List[Dict]:
        """Find modules with highest dependency counts."""
        critical = []

        for module, deps in self.dependencies.items():
            critical.append({
                "module": module,
                "dependents": len(deps["in"]),
                "dependencies": len(deps["out"]),
                "files": self.module_files[module]
            })

        return sorted(critical, key=lambda x: x["dependents"], reverse=True)

    def save_report(self, output_path: Path = Path("dependency_report.json")):
        """Save dependency analysis report."""
        report = {
            "graph": self.generate_graph(),
            "critical_nodes": self.find_critical_nodes()[:20],
            "summary": {
                "total_modules": len(self.dependencies),
                "total_files": sum(len(files) for files in self.module_files.values()),
                "total_edges": sum(len(deps["out"]) for deps in self.dependencies.values())
            }
        }

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"📊 Report saved to {output_path}")


if __name__ == "__main__":
    print("=" * 80)
    print("📦 DEPENDENCY ANALYSIS")
    print("=" * 80)

    mapper = DependencyMapper()
    mapper.map_all()

    print(f"\n📈 SUMMARY:")
    print(f"  Modules: {len(mapper.dependencies)}")
    print(f"  Files: {sum(len(files) for files in mapper.module_files.values())}")

    print("\n🔝 TOP 10 CRITICAL MODULES (by dependents):")
    critical = mapper.find_critical_nodes()[:10]
    for i, node in enumerate(critical, 1):
        print(f"  {i}. {node['module']}")
        print(f"     Dependents: {node['dependents']}, Dependencies: {node['dependencies']}")

    mapper.save_report()
