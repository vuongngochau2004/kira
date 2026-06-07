#!/usr/bin/env python3
"""Check for remaining Protocol imports."""
import os
import re
from pathlib import Path


def check_protocol_imports(root_dir):
    files_with_imports = []
    details = {}

    for py_file in Path(root_dir).rglob("*.py"):
        if any(skip in str(py_file) for skip in ["venv", "__pycache__", ".tox", ".pytest_cache"]):
            continue

        content = py_file.read_text()

        # Check for src.protocols imports
        protocol_matches = re.finditer(r"from src\.protocols\.", content)
        matches = list(protocol_matches)

        if matches:
            relative_path = py_file.relative_to(root_dir)
            files_with_imports.append(str(relative_path))

            # Extract specific imports
            import_lines = []
            for line_num, line in enumerate(content.split('\n'), 1):
                if 'from src.protocols' in line:
                    import_lines.append(f"  Line {line_num}: {line.strip()}")

            details[str(relative_path)] = import_lines

    return files_with_imports, details


if __name__ == "__main__":
    print("=" * 60)
    print("Protocol Import Scan Report")
    print("=" * 60)

    # Check src/
    print("\n📁 Scanning src/...")
    src_files, src_details = check_protocol_imports("src")

    # Check tests/
    print("📁 Scanning tests/...")
    test_files, test_details = check_protocol_imports("tests")

    all_files = src_files + test_files

    print(f"\n📊 Summary:")
    print(f"  - src/ files: {len(src_files)}")
    print(f"  - tests/ files: {len(test_files)}")
    print(f"  - Total: {len(all_files)}")

    if all_files:
        print(f"\n⚠️  Found {len(all_files)} files with Protocol imports:\n")

        # Group by directory
        src_details.update(test_details)

        for file_path in sorted(all_files):
            print(f"📄 {file_path}")
            for line in src_details.get(file_path, []):
                print(line)
            print()
    else:
        print("\n✅ Zero Protocol imports found")

    print("=" * 60)
