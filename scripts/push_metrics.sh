#!/bin/bash
# Push code quality metrics to Prometheus Pushgateway

PUSHGATEWAY_URL="${PUSHGATEWAY_URL:-http://localhost:9091}"
METRICS_FILE="$1"

if [ ! -f "$METRICS_FILE" ]; then
    echo "Error: Metrics file not found: $METRICS_FILE"
    exit 1
fi

JOB_NAME="code_quality"
INSTANCE="raspberrypi-firmware"

echo "Pushing metrics to $PUSHGATEWAY_URL..."
cat "$METRICS_FILE" | curl --data-binary @- -s -o /dev/null -w "%{http_code}" "$PUSHGATEWAY_URL/metrics/job/$JOB_NAME/instance/$INSTANCE"
echo ""

# Verify push
HTTP_CODE=$(cat "$METRICS_FILE" | curl --data-binary @- -s -o /dev/null -w "%{http_code}" "$PUSHGATEWAY_URL/metrics/job/$JOB_NAME/instance/$INSTANCE")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Successfully pushed metrics to Pushgateway"
    exit 0
else
    echo "❌ Failed to push metrics (HTTP $HTTP_CODE)"
    exit 1
fi
