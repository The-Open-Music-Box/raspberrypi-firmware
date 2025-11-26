#!/bin/bash
# Code Quality Metrics Exporter for Prometheus Pushgateway
# This script runs code quality tools and pushes metrics to Prometheus
# Usage: ./export_metrics.sh [pushgateway_url]

set -e

PUSHGATEWAY_URL="${1:-http://localhost:9091}"
JOB_NAME="code_quality"
INSTANCE="${GITHUB_REPOSITORY:-local}"
# Replace slashes in instance name to avoid URL issues
INSTANCE="${INSTANCE//\//-}"

cd "$(dirname "$0")/.."

echo "=== Running Code Quality Tools ==="

# Create metrics file
METRICS_FILE=$(mktemp)

# Function to push metrics to Pushgateway
push_metrics() {
    if [ -s "$METRICS_FILE" ]; then
        echo "Pushing metrics to $PUSHGATEWAY_URL..."
        cat "$METRICS_FILE" | curl --data-binary @- "$PUSHGATEWAY_URL/metrics/job/$JOB_NAME/instance/$INSTANCE"
        echo "Metrics pushed successfully"
    fi
}

# Trap to ensure we push metrics even on error
trap push_metrics EXIT

echo ""
echo "--- mypy (Type Errors) ---"
MYPY_ERRORS=$(mypy app/src --no-error-summary 2>&1 | grep -c "error:" || echo "0")
echo "mypy_errors $MYPY_ERRORS"
cat >> "$METRICS_FILE" << EOF
# HELP mypy_errors Number of type checking errors from mypy
# TYPE mypy_errors gauge
mypy_errors $MYPY_ERRORS
EOF

echo ""
echo "--- bandit (Security Issues) ---"
BANDIT_ISSUES=$(bandit -r app/src -f json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('results', [])))" || echo "0")
echo "bandit_issues $BANDIT_ISSUES"
cat >> "$METRICS_FILE" << EOF
# HELP bandit_security_issues Number of security issues from bandit
# TYPE bandit_security_issues gauge
bandit_security_issues $BANDIT_ISSUES
EOF

echo ""
echo "--- vulture (Dead Code) ---"
VULTURE_ISSUES=$(vulture app/src --min-confidence 80 2>&1 | wc -l | tr -d ' ')
echo "vulture_issues $VULTURE_ISSUES"
cat >> "$METRICS_FILE" << EOF
# HELP vulture_dead_code Number of dead code issues from vulture
# TYPE vulture_dead_code gauge
vulture_dead_code $VULTURE_ISSUES
EOF

echo ""
echo "--- ruff (Linting Issues) ---"
RUFF_ISSUES=$(ruff check app/src --output-format=json 2>/dev/null | python3 -c "import sys, json; print(len(json.load(sys.stdin)))" || echo "0")
echo "ruff_issues $RUFF_ISSUES"
cat >> "$METRICS_FILE" << EOF
# HELP ruff_lint_issues Number of linting issues from ruff
# TYPE ruff_lint_issues gauge
ruff_lint_issues $RUFF_ISSUES
EOF

echo ""
echo "--- interrogate (Docstring Coverage) ---"
DOCSTRING_COVERAGE=$(interrogate app/src -v 2>&1 | grep "TOTAL" | grep -oP '\d+\.\d+(?=%)' || echo "0")
echo "docstring_coverage $DOCSTRING_COVERAGE"
cat >> "$METRICS_FILE" << EOF
# HELP docstring_coverage_percent Docstring coverage percentage from interrogate
# TYPE docstring_coverage_percent gauge
docstring_coverage_percent $DOCSTRING_COVERAGE
EOF

echo ""
echo "--- jscpd (Code Duplication) ---"
DUPLICATION_PERCENT=$(npx jscpd app/src --reporters json --output /tmp 2>/dev/null && cat /tmp/jscpd-report.json | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('statistics', {}).get('total', {}).get('percentage', 0))" || echo "0")
echo "duplication_percent $DUPLICATION_PERCENT"
cat >> "$METRICS_FILE" << EOF
# HELP code_duplication_percent Code duplication percentage from jscpd
# TYPE code_duplication_percent gauge
code_duplication_percent $DUPLICATION_PERCENT
EOF

echo ""
echo "--- radon (Complexity) ---"
# Count functions with high complexity (C or worse)
HIGH_COMPLEXITY=$(radon cc app/src -n C --json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
count = sum(len(funcs) for funcs in data.values())
print(count)
" || echo "0")
echo "high_complexity_functions $HIGH_COMPLEXITY"
cat >> "$METRICS_FILE" << EOF
# HELP high_complexity_functions Number of functions with complexity C or worse
# TYPE high_complexity_functions gauge
high_complexity_functions $HIGH_COMPLEXITY
EOF

# Calculate average complexity
AVG_COMPLEXITY=$(radon cc app/src --average --json 2>/dev/null | python3 -c "
import sys, json
data = json.load(sys.stdin)
total = 0
count = 0
for funcs in data.values():
    for func in funcs:
        total += func.get('complexity', 0)
        count += 1
if count > 0:
    print(round(total / count, 2))
else:
    print(0)
" || echo "0")
echo "avg_complexity $AVG_COMPLEXITY"
cat >> "$METRICS_FILE" << EOF
# HELP average_complexity Average cyclomatic complexity
# TYPE average_complexity gauge
average_complexity $AVG_COMPLEXITY
EOF

echo ""
echo "--- pytest (Test Coverage) ---"
# Run pytest with coverage and extract percentage
COVERAGE_OUTPUT=$(pytest app/tests --cov=app/src --cov-report=term-missing --no-header -q 2>/dev/null || true)
TEST_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep "TOTAL" | awk '{print $NF}' | tr -d '%' || echo "0")
if [ -z "$TEST_COVERAGE" ] || [ "$TEST_COVERAGE" = "0" ]; then
    # Try alternative format
    TEST_COVERAGE=$(echo "$COVERAGE_OUTPUT" | grep -oP '\d+(?=%)' | tail -1 || echo "0")
fi
echo "test_coverage $TEST_COVERAGE"
cat >> "$METRICS_FILE" << EOF
# HELP test_coverage_percent Test coverage percentage from pytest-cov
# TYPE test_coverage_percent gauge
test_coverage_percent $TEST_COVERAGE
EOF

# Count tests
TESTS_TOTAL=$(pytest app/tests --collect-only -q 2>/dev/null | tail -1 | grep -oP '^\d+' || echo "0")
echo "tests_total $TESTS_TOTAL"
cat >> "$METRICS_FILE" << EOF
# HELP tests_total Total number of tests
# TYPE tests_total gauge
tests_total $TESTS_TOTAL
EOF

echo ""
echo "--- Source Lines of Code ---"
SLOC=$(find app/src -name "*.py" -exec cat {} + 2>/dev/null | wc -l | tr -d ' ')
echo "source_lines_of_code $SLOC"
cat >> "$METRICS_FILE" << EOF
# HELP source_lines_of_code Total lines of Python source code
# TYPE source_lines_of_code gauge
source_lines_of_code $SLOC
EOF

echo ""
echo "--- Python File Count ---"
PY_FILES=$(find app/src -name "*.py" | wc -l | tr -d ' ')
echo "python_file_count $PY_FILES"
cat >> "$METRICS_FILE" << EOF
# HELP python_file_count Number of Python source files
# TYPE python_file_count gauge
python_file_count $PY_FILES
EOF

# Add timestamp
TIMESTAMP=$(date +%s)
cat >> "$METRICS_FILE" << EOF
# HELP code_quality_last_update Unix timestamp of last metrics update
# TYPE code_quality_last_update gauge
code_quality_last_update $TIMESTAMP
EOF

echo ""
echo "=== Metrics Collection Complete ==="
echo "Total metrics collected:"
grep -c "^[a-z]" "$METRICS_FILE" || echo "0"
