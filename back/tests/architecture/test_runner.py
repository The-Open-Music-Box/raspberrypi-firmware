# Copyright (c) 2025 Jonathan Piette
# This file is part of TheOpenMusicBox and is licensed for non-commercial use only.
# See the LICENSE file for details.

"""Architecture Testing Suite Runner.

This module provides a comprehensive test runner for all architecture tests
and generates detailed reports about DDD compliance.
"""

import pytest
import os
import sys
from typing import Dict, List, Tuple
from tests.architecture.helpers import (
    build_dependency_graph,
    get_layer_from_module,
    get_project_root,
    get_all_python_files,
    find_circular_dependencies,
    validate_ddd_layer_dependencies,
    check_naming_conventions
)


class ArchitectureTestRunner:
    """Main runner for architecture compliance tests."""

    def __init__(self):
        """Initialize the test runner."""
        self.project_root = get_project_root()
        self.dependency_graph = build_dependency_graph()

    def run_all_tests(self) -> Dict[str, any]:
        """Run all architecture tests and return comprehensive results.

        Returns:
            Dictionary containing test results and metrics
        """
        results = {
            'domain_purity': self._test_domain_purity(),
            'dependency_direction': self._test_dependency_direction(),
            'circular_dependencies': self._test_circular_dependencies(),
            'class_placement': self._test_class_placement(),
            'naming_conventions': self._test_naming_conventions(),
            'overall_score': 0,
            'recommendations': []
        }

        # Calculate overall score
        results['overall_score'] = self._calculate_overall_score(results)
        results['recommendations'] = self._generate_recommendations(results)

        return results

    def _test_domain_purity(self) -> Dict[str, any]:
        """Test Domain layer purity."""
        violations = []
        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        forbidden_imports = [
            "app.src.infrastructure",
            "app.src.application",
            "app.src.services",
            "fastapi",
            "sqlalchemy",
            "requests"
        ]

        for file_path in domain_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for forbidden in forbidden_imports:
                    if forbidden in content:
                        violations.append(f"Domain imports {forbidden}: {file_path}")
            except Exception:
                continue

        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'score': 100 if len(violations) == 0 else max(0, 100 - len(violations) * 10)
        }

    def _test_dependency_direction(self) -> Dict[str, any]:
        """Test dependency direction compliance."""
        violations = validate_ddd_layer_dependencies(self.dependency_graph)

        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'score': 100 if len(violations) == 0 else max(0, 100 - len(violations) * 5)
        }

    def _test_circular_dependencies(self) -> Dict[str, any]:
        """Test for circular dependencies."""
        cycles = find_circular_dependencies(self.dependency_graph)

        return {
            'passed': len(cycles) == 0,
            'violations': cycles,
            'score': 100 if len(cycles) == 0 else max(0, 100 - len(cycles) * 20)
        }

    def _test_class_placement(self) -> Dict[str, any]:
        """Test class placement correctness."""
        violations = []

        # Check for controllers in domain
        domain_path = os.path.join(self.project_root, "app", "src", "domain")
        domain_files = get_all_python_files(domain_path)

        for file_path in domain_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                if "Controller" in content and "class" in content:
                    violations.append(f"Controller class in Domain: {file_path}")
            except Exception:
                continue

        return {
            'passed': len(violations) == 0,
            'violations': violations,
            'score': 100 if len(violations) == 0 else max(0, 100 - len(violations) * 15)
        }

    def _test_naming_conventions(self) -> Dict[str, any]:
        """Test naming conventions."""
        violations = check_naming_conventions()
        error_violations = [v for v in violations if v.startswith("❌")]

        return {
            'passed': len(error_violations) == 0,
            'violations': error_violations,
            'score': 100 if len(error_violations) == 0 else max(0, 100 - len(error_violations) * 3)
        }

    def _calculate_overall_score(self, results: Dict[str, any]) -> int:
        """Calculate overall architecture score."""
        scores = []
        weights = {
            'domain_purity': 0.3,      # 30% - Most critical
            'dependency_direction': 0.25,  # 25% - Very important
            'circular_dependencies': 0.25,  # 25% - Very important
            'class_placement': 0.15,       # 15% - Important
            'naming_conventions': 0.05     # 5% - Nice to have
        }

        total_score = 0
        for category, weight in weights.items():
            if category in results and 'score' in results[category]:
                total_score += results[category]['score'] * weight

        return int(total_score)

    def _generate_recommendations(self, results: Dict[str, any]) -> List[str]:
        """Generate recommendations based on test results."""
        recommendations = []

        if not results['domain_purity']['passed']:
            recommendations.append(
                "🔥 CRITICAL: Purify Domain layer by removing external dependencies"
            )

        if not results['dependency_direction']['passed']:
            recommendations.append(
                "🔥 CRITICAL: Fix dependency direction violations to follow DDD rules"
            )

        if not results['circular_dependencies']['passed']:
            recommendations.append(
                "⚠️ HIGH: Eliminate circular dependencies to improve maintainability"
            )

        if not results['class_placement']['passed']:
            recommendations.append(
                "📋 MEDIUM: Move misplaced classes to appropriate architectural layers"
            )

        if not results['naming_conventions']['passed']:
            recommendations.append(
                "📝 LOW: Improve naming conventions for better code readability"
            )

        if results['overall_score'] >= 90:
            recommendations.append("🎉 EXCELLENT: Architecture meets DDD excellence standards!")
        elif results['overall_score'] >= 80:
            recommendations.append("✅ GOOD: Architecture is solid with minor improvements needed")
        elif results['overall_score'] >= 70:
            recommendations.append("⚠️ FAIR: Architecture needs attention to reach DDD standards")
        else:
            recommendations.append("🚨 POOR: Architecture requires significant refactoring")

        return recommendations

    def generate_report(self) -> str:
        """Generate a comprehensive architecture report."""
        results = self.run_all_tests()

        report = f"""
# Architecture Testing Suite Report
## The Open Music Box - DDD Compliance Analysis

### Overall Score: {results['overall_score']}/100

### Test Results Summary:

#### 🏛️ Domain Layer Purity: {'✅ PASS' if results['domain_purity']['passed'] else '❌ FAIL'} ({results['domain_purity']['score']}/100)
{f"Violations: {len(results['domain_purity']['violations'])}" if results['domain_purity']['violations'] else "No violations found"}

#### 🔄 Dependency Direction: {'✅ PASS' if results['dependency_direction']['passed'] else '❌ FAIL'} ({results['dependency_direction']['score']}/100)
{f"Violations: {len(results['dependency_direction']['violations'])}" if results['dependency_direction']['violations'] else "No violations found"}

#### 🔗 Circular Dependencies: {'✅ PASS' if results['circular_dependencies']['passed'] else '❌ FAIL'} ({results['circular_dependencies']['score']}/100)
{f"Cycles found: {len(results['circular_dependencies']['violations'])}" if results['circular_dependencies']['violations'] else "No circular dependencies"}

#### 📍 Class Placement: {'✅ PASS' if results['class_placement']['passed'] else '❌ FAIL'} ({results['class_placement']['score']}/100)
{f"Misplaced classes: {len(results['class_placement']['violations'])}" if results['class_placement']['violations'] else "All classes properly placed"}

#### 📝 Naming Conventions: {'✅ PASS' if results['naming_conventions']['passed'] else '❌ FAIL'} ({results['naming_conventions']['score']}/100)
{f"Naming violations: {len(results['naming_conventions']['violations'])}" if results['naming_conventions']['violations'] else "All naming conventions followed"}

### Recommendations:
{chr(10).join([f"- {rec}" for rec in results['recommendations']])}

### Architecture Statistics:
- Total modules analyzed: {len(self.dependency_graph)}
- Dependency relationships: {sum(len(deps) for deps in self.dependency_graph.values())}

### Layer Distribution:
"""

        # Add layer statistics
        layer_stats = {}
        for module in self.dependency_graph.keys():
            layer = get_layer_from_module(module)
            layer_stats[layer] = layer_stats.get(layer, 0) + 1

        for layer, count in sorted(layer_stats.items()):
            report += f"- {layer.title()}: {count} modules\n"

        report += f"""
Generated on: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        return report


def main():
    """Main entry point for running architecture tests."""
    runner = ArchitectureTestRunner()
    report = runner.generate_report()
    print(report)

    # Save report to file
    report_path = os.path.join(runner.project_root, "ARCHITECTURE_TEST_REPORT.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📄 Report saved to: {report_path}")


if __name__ == "__main__":
    main()