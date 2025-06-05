#!/bin/bash
# Script to update the jira2pr-cronjob.yaml to use the ConfigMap

set -e

./create-jira2pr-secrets.sh
./create-jira2pr-configmap.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRONJOB_PATH="${SCRIPT_DIR}/jira2pr-cronjob.yaml"

# Ensure the cronjob file exists
if [ ! -f "$CRONJOB_PATH" ]; then
  echo "Error: CronJob YAML not found at $CRONJOB_PATH"
  exit 1
fi

# Create the updated CronJob YAML
cat > "$CRONJOB_PATH" << EOF
apiVersion: batch/v1
kind: CronJob
metadata:
  name: jira2pr-batch-update
  namespace: default
spec:
  schedule: "0/2 * * * *" # Run every 2 minutes
  concurrencyPolicy: Forbid
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: jira2pr
            image: python:3.13-slim
            command:
            - /bin/bash
            - -c
            - |
              pip install requests
              python /scripts/jira2pr.py --batch-update
            env:
            - name: JIRA_URL
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: jira-url
            - name: JIRA_USERNAME
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: jira-username
            - name: JIRA_API_TOKEN
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: jira-api-token
            - name: GITHUB_TOKEN
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: github-token
            - name: GITHUB_OWNER
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: github-owner
            - name: GITHUB_REPO
              valueFrom:
                secretKeyRef:
                  name: jira2pr-secrets
                  key: github-repo
            volumeMounts:
            - name: script-volume
              mountPath: /scripts
          volumes:
          - name: script-volume
            configMap:
              name: jira2pr-script
              defaultMode: 0755
          restartPolicy: OnFailure
EOF

echo "CronJob YAML updated at $CRONJOB_PATH"
echo "Remember to apply both the ConfigMap and CronJob to your cluster:"
echo "kubectl apply -f ${SCRIPT_DIR}/jira2pr-secrets.yaml"
echo "kubectl apply -f ${SCRIPT_DIR}/jira2pr-configmap.yaml"
echo "kubectl apply -f $CRONJOB_PATH"
