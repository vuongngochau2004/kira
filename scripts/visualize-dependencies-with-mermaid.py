#!/usr/bin/env python3
"""Generate dependency graph visualization using Mermaid."""
import json
from pathlib import Path


def generate_mermaid_graph(report_path: Path = Path("dependency_report.json")):
    """Generate Mermaid flowchart from dependency report."""

    if not report_path.exists():
        print(f"❌ Report not found: {report_path}")
        print("Run analyze-dependencies-for-modular-monolith.py first")
        return

    with open(report_path) as f:
        report = json.load(f)

    # Group by layer
    layers = {
        "serving": [],
        "agent_tools": [],
        "retrieval": [],
        "ingestion": [],
        "abstractions": [],
        "storage": []
    }

    for node in report["graph"]["nodes"]:
        module = node["id"]
        if module.startswith("api"):
            layers["serving"].append(module)
        elif any(module.startswith(x) for x in ["agents", "handlers", "classification", "tools", "graphs"]):
            layers["agent_tools"].append(module)
        elif any(module.startswith(x) for x in ["retrieval", "indexing"]):
            layers["retrieval"].append(module)
        elif module.startswith("ingestion"):
            layers["ingestion"].append(module)
        elif any(module.startswith(x) for x in ["interfaces", "di"]):
            layers["abstractions"].append(module)
        else:
            layers["storage"].append(module)

    # Generate Mermaid graph
    mermaid = ["graph TD"]

    # Add subgraphs for layers
    for layer_name, modules in layers.items():
        if modules:
            mermaid.append(f"  subgraph {layer_name.upper()}[{layer_name}]")
            for module in modules[:5]:  # Limit to 5 per layer
                clean_id = module.replace(".", "_").replace("-", "_")
                mermaid.append(f"    {clean_id}[\"{module}\"]")
            mermaid.append("  end")

    # Add edges (limit to prevent clutter)
    edges = report["graph"]["edges"][:50]
    for edge in edges:
        from_node = edge["from"].replace(".", "_").replace("-", "_")
        to_node = edge["to"].replace(".", "_").replace("-", "_")
        mermaid.append(f"  {from_node} --> {to_node}")

    # Output
    output = "\n".join(mermaid)

    output_file = Path("dependency-graph.mmd")
    with open(output_file, "w") as f:
        f.write(output)

    print(f"📊 Mermaid graph saved to {output_file}")
    print("\n🌐 View online: https://mermaid.live\n")
    print("Copy the content below to mermaid.live:\n")
    print(output)


if __name__ == "__main__":
    generate_mermaid_graph()
