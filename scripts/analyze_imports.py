#!/usr/bin/env python3
"""Analyze Protocol imports by category."""
import re
from pathlib import Path
from collections import defaultdict


def categorize_imports(root_dir):
    """Categorize imports by type and purpose."""
    categories = defaultdict(lambda: defaultdict(list))

    for py_file in Path(root_dir).rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".tox", ".pytest_cache"]):
            continue

        content = py_file.read_text()
        relative_path = str(py_file.relative_to(root_dir))

        for line_num, line in enumerate(content.split('\n'), 1):
            if 'from src.protocols' in line:
                # Determine category based on file location
                if relative_path.startswith('protocols/'):
                    if '>>>' in line:
                        categories['protocols']['docstring_examples'].append((relative_path, line_num, line.strip()))
                    elif relative_path.endswith('__init__.py'):
                        categories['protocols']['init_exports'].append((relative_path, line_num, line.strip()))
                    else:
                        categories['protocols']['definitions'].append((relative_path, line_num, line.strip()))

                elif relative_path.startswith('abc/'):
                    categories['abc']['imports'].append((relative_path, line_num, line.strip()))

                elif relative_path.startswith('tests/'):
                    categories['tests']['imports'].append((relative_path, line_num, line.strip()))

                elif relative_path.startswith('fixtures/'):
                    categories['fixtures']['imports'].append((relative_path, line_num, line.strip()))

                else:
                    # Regular source code
                    categories['source']['imports'].append((relative_path, line_num, line.strip()))

    return categories


if __name__ == "__main__":
    print("=" * 70)
    print("Protocol Import Analysis by Category")
    print("=" * 70)

    categories = categorize_imports(".")

    print("\n📋 SUMMARY BY CATEGORY:\n")

    total_count = 0

    # Order matters: show least problematic first
    for cat_name in ['protocols', 'abc', 'source', 'fixtures', 'tests']:
        if cat_name not in categories:
            continue

        cat_data = categories[cat_name]
        cat_count = sum(len(items) for items in cat_data.values())
        total_count += cat_count

        print(f"📂 {cat_name.upper()}: {cat_count} imports")

        for subcat, items in cat_data.items():
            if items:
                print(f"   └─ {subcat}: {len(items)}")

    print(f"\n📊 TOTAL: {total_count} Protocol imports")

    print("\n" + "=" * 70)
    print("DETAILED BREAKDOWN")
    print("=" * 70)

    for cat_name in ['source', 'abc', 'fixtures', 'tests', 'protocols']:
        if cat_name not in categories:
            continue

        print(f"\n{'─' * 70}")
        print(f"📂 {cat_name.upper()}")
        print(f"{'─' * 70}")

        for subcat, items in categories[cat_name].items():
            if not items:
                continue

            print(f"\n  📁 {subcat} ({len(items)} files):")

            for file_path, line_num, line in sorted(items):
                print(f"     {file_path}:{line_num}")
                print(f"       {line}")

    print("\n" + "=" * 70)
