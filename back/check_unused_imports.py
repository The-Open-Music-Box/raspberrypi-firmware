#!/usr/bin/env python3
"""Simple script to check for potentially unused imports."""

import ast
import sys
from pathlib import Path
from typing import Set, List, Tuple


class ImportChecker(ast.NodeVisitor):
    """AST visitor to check for unused imports."""

    def __init__(self, source: str):
        self.source = source
        self.imports: Set[str] = set()
        self.used_names: Set[str] = set()
        self.import_locations: dict = {}

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name.split('.')[0]
            self.imports.add(name)
            self.import_locations[name] = node.lineno
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            if alias.name == '*':
                continue  # Skip star imports
            name = alias.asname if alias.asname else alias.name
            self.imports.add(name)
            self.import_locations[name] = node.lineno
        self.generic_visit(node)

    def visit_Name(self, node):
        if not isinstance(node.ctx, ast.Store):
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node):
        # Track the root name in attribute access
        if isinstance(node.value, ast.Name):
            self.used_names.add(node.value.id)
        self.generic_visit(node)

    def get_unused_imports(self) -> List[Tuple[str, int]]:
        """Return list of (import_name, line_number) for unused imports."""
        unused = []
        for imp in self.imports:
            if imp not in self.used_names:
                unused.append((imp, self.import_locations[imp]))
        return sorted(unused, key=lambda x: x[1])


def check_file(filepath: Path) -> List[Tuple[str, int]]:
    """Check a single file for unused imports."""
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
        checker = ImportChecker(source)
        checker.visit(tree)
        return checker.get_unused_imports()
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Check all Python files in app/src for unused imports."""
    base_dir = Path("app/src")
    files_with_issues = []

    for filepath in base_dir.rglob("*.py"):
        unused = check_file(filepath)
        if unused:
            files_with_issues.append((filepath, unused))

    if files_with_issues:
        print("Files with potentially unused imports:\n")
        for filepath, unused in files_with_issues:
            print(f"{filepath}:")
            for name, lineno in unused:
                print(f"  Line {lineno}: {name}")
            print()
    else:
        print("No obvious unused imports found.")


if __name__ == "__main__":
    main()
