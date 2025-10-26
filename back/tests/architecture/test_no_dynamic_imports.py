# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Architecture test: No dynamic imports allowed.

This test ensures the codebase doesn't use importlib.import_module(),
which causes IDE issues, debugging problems, and hides the dependency graph.
"""

import os
import re
import pytest
from pathlib import Path


def get_python_files(base_path: Path) -> list[Path]:
    """Get all Python files in the application source."""
    python_files = []
    for root, dirs, files in os.walk(base_path):
        # Skip test directories and __pycache__
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'tests', '.pytest_cache']]

        for file in files:
            if file.endswith('.py'):
                python_files.append(Path(root) / file)

    return python_files


def check_file_for_dynamic_imports(file_path: Path) -> list[tuple[int, str]]:
    """Check a file for dynamic import usage.

    Returns:
        List of (line_number, line_content) tuples for violations
    """
    violations = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, start=1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('#'):
                continue

            # Check for importlib.import_module
            if re.search(r'importlib\.import_module\s*\(', line):
                violations.append((line_num, line.rstrip()))

    return violations


class TestNoDynamicImports:
    """Ensure no dynamic imports are used in the codebase."""

    @pytest.fixture
    def app_src_path(self) -> Path:
        """Get the application source path."""
        # From tests/architecture, go up to project root, then to app/src
        return Path(__file__).parent.parent.parent / 'app' / 'src'

    def test_no_importlib_import_module(self, app_src_path: Path):
        """Ensure no files use importlib.import_module().

        Dynamic imports cause several issues:
        - Breaks IDE autocomplete and go-to-definition
        - Makes debugging harder (stack traces show importlib, not actual code)
        - Hides dependency graph
        - Prevents static analysis
        - Performance overhead

        Solution: Use proper dependency injection via the DI container.
        """
        all_violations = {}
        python_files = get_python_files(app_src_path)

        assert python_files, "No Python files found in app/src"

        for file_path in python_files:
            violations = check_file_for_dynamic_imports(file_path)
            if violations:
                # Store relative path for cleaner output
                rel_path = file_path.relative_to(app_src_path.parent.parent)
                all_violations[str(rel_path)] = violations

        if all_violations:
            # Build detailed error message
            error_msg = [
                "\n❌ Dynamic imports found (importlib.import_module):",
                f"\nTotal files with violations: {len(all_violations)}",
                f"Total violations: {sum(len(v) for v in all_violations.values())}",
                "\nViolations by file:\n"
            ]

            for file_path, violations in sorted(all_violations.items()):
                error_msg.append(f"\n  {file_path}:")
                for line_num, line_content in violations:
                    error_msg.append(f"    Line {line_num}: {line_content}")

            error_msg.extend([
                "\n\n🔧 Fix:",
                "  1. Replace importlib.import_module() with direct imports",
                "  2. Use the DI container for runtime dependency resolution",
                "  3. Use protocols/interfaces to break circular dependencies",
                "\nExample:",
                "  # BAD",
                "  SomeClass = importlib.import_module('module').SomeClass",
                "",
                "  # GOOD",
                "  from module import SomeClass",
                "",
                "  # GOOD (if circular dependency)",
                "  from typing import TYPE_CHECKING",
                "  if TYPE_CHECKING:",
                "      from module import SomeClass",
            ])

            pytest.fail('\n'.join(error_msg))

    def test_progress_tracking(self, app_src_path: Path):
        """Track progress of dynamic import elimination.

        This test always passes but logs the current state.
        """
        python_files = get_python_files(app_src_path)
        total_violations = 0
        files_with_violations = 0

        for file_path in python_files:
            violations = check_file_for_dynamic_imports(file_path)
            if violations:
                files_with_violations += 1
                total_violations += len(violations)

        total_files = len(python_files)
        clean_files = total_files - files_with_violations
        progress = (clean_files / total_files * 100) if total_files > 0 else 0

        print(f"\n📊 Dynamic Import Elimination Progress:")
        print(f"  Total Python files: {total_files}")
        print(f"  Files without dynamic imports: {clean_files}")
        print(f"  Files with dynamic imports: {files_with_violations}")
        print(f"  Total dynamic imports remaining: {total_violations}")
        print(f"  Progress: {progress:.1f}% complete")
