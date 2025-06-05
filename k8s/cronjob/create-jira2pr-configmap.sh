#!/bin/bash
# Script to generate a Kubernetes ConfigMap from the jira2pr.py script

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="${SCRIPT_DIR}/../../jira2pr/jira2pr.py"
OUTPUT_PATH="${SCRIPT_DIR}/jira2pr-configmap.yaml"

# Ensure the script exists
if [ ! -f "$SCRIPT_PATH" ]; then
  echo "Error: Script not found at $SCRIPT_PATH"
  exit 1
fi

# Create the ConfigMap YAML
cat > "$OUTPUT_PATH" << EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: jira2pr-script
  namespace: default
data:
  jira2pr.py: |
EOF

# Append the script content with proper indentation
sed 's/^/    /' "$SCRIPT_PATH" >> "$OUTPUT_PATH"

echo "ConfigMap generated at $OUTPUT_PATH"
echo "To apply it to your cluster, run: kubectl apply -f $OUTPUT_PATH"
