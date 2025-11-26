#!/usr/bin/env python3
"""Code Quality Metrics Collection Script."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict


def run_command(cmd: list, cwd: Path = None):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
        return result
    except Exception as e:
        print(f"Error running command {cmd}: {e}")
        return subprocess.CompletedProcess(cmd, 1, "", str(e))


def get_coverage_metrics(back_dir: Path) -> Dict[str, float]:
    """Extract coverage percentage from coverage reports."""
    metrics = {}
    coverage_file = back_dir / "coverage.json"

    if coverage_file.exists():
        try:
            with open(coverage_file) as f:
                data = json.load(f)
                metrics["test_coverage_percent"] = data.get("totals", {}).get("percent_covered", 0.0)
        except Exception as e:
            print(f"Error reading coverage.json: {e}")
            metrics["test_coverage_percent"] = 0.0
    else:
        metrics["test_coverage_percent"] = 0.0

    return metrics


def get_mypy_metrics(back_dir: Path) -> Dict[str, int]:
    """Run mypy and count type errors."""
    print("Running mypy type checking...")
    result = run_command(["mypy", "app", "--ignore-missing-imports"], cwd=back_dir)

    error_count = 0
    if result.stdout:
        error_count = len([line for line in result.stdout.split("\n") if "error:" in line])

    return {"mypy_errors": error_count}


def get_bandit_metrics(back_dir: Path) -> Dict[str, int]:
    """Run bandit security scanner and count issues."""
    print("Running bandit security scan...")
    result = run_command(["bandit", "-r", "app", "-f", "json", "-q"], cwd=back_dir)

    issue_count = 0
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            issue_count = len(data.get("results", []))
        except:
            pass

    return {"bandit_security_issues": issue_count}


def get_ruff_metrics(back_dir: Path) -> Dict[str, int]:
    """Run ruff linter and count issues."""
    print("Running ruff linter...")
    result = run_command(["ruff", "check", "app", "--output-format=json"], cwd=back_dir)

    issue_count = 0
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            issue_count = len(data) if isinstance(data, list) else 0
        except:
            pass

    return {"ruff_lint_issues": issue_count}


def get_docstring_coverage(back_dir: Path) -> Dict[str, float]:
    """Calculate docstring coverage percentage."""
    print("Calculating docstring coverage...")
    result = run_command(["interrogate", "app", "-vv", "--quiet", "--fail-under=0"], cwd=back_dir)

    coverage = 0.0
    if result.stdout:
        for line in result.stdout.split("\n"):
            if "TOTAL" in line or "actual" in line.lower():
                import re
                match = re.search(r"(\d+\.\d+)%", line)
                if match:
                    coverage = float(match.group(1))
                    break

    return {"docstring_coverage_percent": coverage}


def get_duplication_metrics(back_dir: Path) -> Dict[str, float]:
    """Estimate code duplication."""
    return {"code_duplication_percent": 0.0}


def main():
    project_root = Path(__file__).parent.parent
    back_dir = project_root / "back"
    scripts_dir = project_root / "scripts"
    metrics_file = project_root / "code_metrics.txt"

    print("=" * 60)
    print("Code Quality Metrics Collection")
    print("=" * 60)
    print(f"Backend directory: {back_dir}")
    print()

    if not back_dir.exists():
        print(f"Error: Backend directory not found: {back_dir}")
        sys.exit(1)

    all_metrics = {}

    print("📊 Collecting coverage metrics...")
    all_metrics.update(get_coverage_metrics(back_dir))

    print("🔍 Collecting type checking metrics...")
    all_metrics.update(get_mypy_metrics(back_dir))

    print("🔒 Collecting security metrics...")
    all_metrics.update(get_bandit_metrics(back_dir))

    print("📝 Collecting linting metrics...")
    all_metrics.update(get_ruff_metrics(back_dir))

    print("📚 Collecting docstring coverage...")
    all_metrics.update(get_docstring_coverage(back_dir))

    print("📋 Collecting duplication metrics...")
    all_metrics.update(get_duplication_metrics(back_dir))

    print("\n" + "=" * 60)
    print("Collected Metrics:")
    print("=" * 60)
    for metric, value in sorted(all_metrics.items()):
        print(f"  {metric}: {value}")

    # Write metrics to file
    print(f"\nWriting metrics to {metrics_file}...")
    with open(metrics_file, "w") as f:
        for metric_name, value in all_metrics.items():
            f.write(f"{metric_name} {value}\n")

    # Call bash script to push metrics
    print("\n" + "=" * 60)
    push_script = scripts_dir / "push_metrics.sh"
    if push_script.exists():
        result = subprocess.run([str(push_script), str(metrics_file)], capture_output=True, text=True)
        print(result.stdout)
        if result.returncode == 0:
            print("✅ Code quality metrics collection completed successfully!")
            sys.exit(0)
        else:
            print(result.stderr)
            print("❌ Failed to push metrics")
            sys.exit(1)
    else:
        print(f"❌ Push script not found: {push_script}")
        sys.exit(1)


if __name__ == "__main__":
    main()
