#!/usr/bin/env python
"""Generate test coverage reports for TheOpenMusicBox application.

This script runs the test suite with coverage reporting enabled and
generates both HTML and console reports to help identify areas that need
more testing.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Generate test coverage reports")
    parser.add_argument(
        "--format",
        choices=["html", "term", "xml", "all"],
        default="all",
        help="Coverage report format (default: all)",
    )
    parser.add_argument(
        "--min-coverage",
        type=int,
        default=70,
        help="Minimum required coverage percentage (default: 70)",
    )
    parser.add_argument(
        "--markers",
        type=str,
        default=None,
        help="Only run tests with these markers (e.g., 'api and not slow')",
    )
    return parser.parse_args()


def run_coverage(args):
    """Run tests with coverage and generate reports."""
    # Ensure we're in the back directory
    os.chdir(Path(__file__).parent)

    # Build the command using start_test.py which is designed for TheOpenMusicBox
    cmd = ["python", "start_test.py"]

    # Add markers if specified
    if args.markers:
        cmd.extend(["-m", args.markers])

    # Add coverage options
    cmd.append("--cov")

    # Add additional coverage options based on format
    if args.format == "all" or args.format == "html":
        cmd.append("--cov-report=html")
    if args.format == "all" or args.format == "xml":
        cmd.append("--cov-report=xml")
    if args.format == "all" or args.format == "term":
        cmd.append("--cov-report=term-missing")

    # Run the command
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Print the output
    print("\n--- STDOUT ---")
    print(result.stdout)

    print("\n--- STDERR ---")
    print(result.stderr)

    # Check for coverage percentage
    if args.format == "all" or args.format == "term":
        coverage_line = next(
            (
                line
                for line in result.stdout.split("\n")
                if "TOTAL" in line and "%" in line
            ),
            None,
        )
        if coverage_line:
            try:
                coverage_pct = int(coverage_line.split("%")[0].split()[-1])
                print(f"\nTotal coverage: {coverage_pct}%")
                if coverage_pct < args.min_coverage:
                    print(
                        f"WARNING: Coverage is below the minimum threshold of {args.min_coverage}%"
                    )
                    return 1
            except (ValueError, IndexError):
                print("Could not parse coverage percentage")

    return result.returncode


def main():
    """Main entry point."""
    args = parse_args()
    try:
        return run_coverage(args)
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        print(f"Error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
