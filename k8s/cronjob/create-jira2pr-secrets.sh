#!/bin/bash

# Path to your .envrc file
ENVRC_FILE="../../.envrc"


# Output files
SECRET_YAML="jira2pr-secrets.yaml"
VALUES_YAML_SNIPPET="values-snippet.yaml"

# Check if the .envrc file exists
if [[ ! -f "$ENVRC_FILE" ]]; then
    echo "Error: $ENVRC_FILE not found"
    exit 1
fi

# Initialize output files
echo "apiVersion: v1
kind: Secret
metadata:
  name: jira2pr-secrets
type: Opaque
data:" > "$SECRET_YAML"

echo "jira2pr:
  extraEnv:" > "$VALUES_YAML_SNIPPET"

# Process each line in the .envrc file
while IFS= read -r line || [[ -n "$line" ]]; do
    # Skip empty lines and comments
    if [[ -z "$line" || "$line" =~ ^# ]]; then
        continue
    fi

    # Extract environment variable names and values
    if [[ "$line" =~ ^export\ ([A-Za-z0-9_]+)=\"?([^\"]*)\"? ]]; then
        VAR_NAME="${BASH_REMATCH[1]}"
        VAR_VALUE="${BASH_REMATCH[2]}"

        # Convert to lowercase for secret key and create a formatted key
        SECRET_KEY=$(echo "$VAR_NAME" | tr '[:upper:]' '[:lower:]' | tr '_' '-')

        # Create SECRET_ prefixed environment variable name
        SECRET_ENV_NAME="SECRET_${VAR_NAME}"

        # Base64 encode the value for the Kubernetes secret
        BASE64_VALUE=$(echo -n "$VAR_VALUE" | base64)

        # Append to secret YAML
        echo "  $SECRET_KEY: $BASE64_VALUE" >> "$SECRET_YAML"

        # Append to values YAML snippet
        echo "    - name: $SECRET_ENV_NAME
      valueFrom:
        secretKeyRef:
          name: kestra-secrets
          key: $SECRET_KEY" >> "$VALUES_YAML_SNIPPET"
    fi
done < "$ENVRC_FILE"

echo "Generated files:"
echo "  - $SECRET_YAML (Kubernetes Secret definition)"
echo "  - $VALUES_YAML_SNIPPET (Snippet to add to your values.yaml)"
echo "Apply the Secret with: kubectl apply -f $SECRET_YAML"
echo "Add the contents of $VALUES_YAML_SNIPPET to your Helm values.yaml"
