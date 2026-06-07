#!/usr/bin/env python3
"""Categorize Protocol imports by migration priority."""
import re
from pathlib import Path


def analyze_import_needs():
    """Analyze which imports need migration vs are acceptable."""
    analysis = {
        'keep': [],          # Docstring examples, __init__ exports
        'migrate_high': [],  # Core business logic files
        'migrate_medium': [],# Support files
        'migrate_low': [],   # Test files, fixtures
    }

    for py_file in Path(".").rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".tox", ".pytest_cache", "scripts"]):
            continue

        content = py_file.read_text()
        relative_path = str(py_file)

        for line_num, line in enumerate(content.split('\n'), 1):
            if 'from src.protocols' not in line:
                continue

            # Docstring examples (KEEP)
            if '>>>' in line:
                analysis['keep'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'Docstring example',
                    'import': line.strip()
                })

            # __init__.py exports (KEEP - these re-export from protocols)
            elif relative_path.endswith('src/protocols/__init__.py'):
                analysis['keep'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'Package exports',
                    'import': line.strip()
                })

            # Core business logic (HIGH PRIORITY)
            elif any(path in relative_path for path in [
                'src/classification/strategies/',
                'src/handlers/',
                'src/di/',
                'src/classification/cache/',
            ]):
                analysis['migrate_high'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'Core business logic',
                    'import': line.strip()
                })

            # ABC implementations (HIGH PRIORITY - need to use src.abc instead)
            elif 'src/abc/' in relative_path:
                analysis['migrate_high'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'ABC implementation (should use src.abc)',
                    'import': line.strip()
                })

            # Test utilities (MEDIUM)
            elif any(path in relative_path for path in [
                'tests/fixtures/',
                'tools/',
            ]):
                analysis['migrate_medium'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'Test/support utilities',
                    'import': line.strip()
                })

            # Test files (LOW - can keep using protocols for type checking)
            elif 'tests/' in relative_path:
                analysis['migrate_low'].append({
                    'file': relative_path,
                    'line': line_num,
                    'reason': 'Test file (acceptable for now)',
                    'import': line.strip()
                })

    return analysis


if __name__ == "__main__":
    print("=" * 80)
    print("PROTOCOL IMPORT MIGRATION ANALYSIS")
    print("=" * 80)

    analysis = analyze_import_needs()

    print("\n📊 SUMMARY:\n")
    print(f"  ✅ KEEP (acceptable):      {len(analysis['keep'])} imports")
    print(f"  🔴 MIGRATE HIGH (core):    {len(analysis['migrate_high'])} imports")
    print(f"  🟡 MIGRATE MEDIUM (utils): {len(analysis['migrate_medium'])} imports")
    print(f"  🟢 MIGRATE LOW (tests):    {len(analysis['migrate_low'])} imports")
    print(f"  ─────────────────────────────────────────")
    print(f"  📈 TOTAL:                  {sum(len(v) for v in analysis.values())} imports")

    print("\n" + "=" * 80)
    print("HIGH PRIORITY MIGRATIONS (Core Business Logic)")
    print("=" * 80)

    if analysis['migrate_high']:
        print(f"\n🔴 {len(analysis['migrate_high'])} files need migration:\n")
        for item in analysis['migrate_high']:
            print(f"  📄 {item['file']}:{item['line']}")
            print(f"     {item['import']}")
            print(f"     Reason: {item['reason']}\n")
    else:
        print("\n✅ No high-priority migrations needed!\n")

    print("=" * 80)
    print("MEDIUM PRIORITY MIGRATIONS (Utilities)")
    print("=" * 80)

    if analysis['migrate_medium']:
        print(f"\n🟡 {len(analysis['migrate_medium'])} files:\n")
        for item in analysis['migrate_medium']:
            print(f"  📄 {item['file']}:{item['line']}")
            print(f"     {item['import']}\n")
    else:
        print("\n✅ No medium-priority migrations needed!\n")

    print("=" * 80)
    print("LOW PRIORITY (Tests - Acceptable)")
    print("=" * 80)

    if analysis['migrate_low']:
        print(f"\n🟢 {len(analysis['migrate_low'])} test imports (acceptable for type checking):\n")
        for item in analysis['migrate_low'][:10]:  # Show first 10
            print(f"  📄 {item['file']}:{item['line']}")
        if len(analysis['migrate_low']) > 10:
            print(f"  ... and {len(analysis['migrate_low']) - 10} more")
    else:
        print("\n✅ No test imports found!\n")

    print("\n" + "=" * 80)
    print("KEEP (Docstrings & Exports)")
    print("=" * 80)

    if analysis['keep']:
        print(f"\n✅ {len(analysis['keep'])} acceptable imports:\n")
        for item in analysis['keep']:
            print(f"  📄 {item['file']}:{item['line']}")
            print(f"     {item['reason']}: {item['import'][:60]}...\n")
    else:
        print("\n✅ No imports to keep!\n")

    print("=" * 80)
