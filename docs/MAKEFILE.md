# Makefile Usage Guide

This document describes the available Make targets for the jira2pr project.

## Prerequisites

- `make` command available
- `uv` installed for Python dependency management
- `kubectl` installed (for Kubernetes deployment)
- `helm` installed (for Helm deployment)
- `gh` CLI installed (for GitHub Actions)

## Basic Usage

### Installation and Setup

```bash
# Install dependencies
make install

# Check environment variables
make check-env
```

### Running the Tool

```bash
# Run for a specific ticket
make run TICKET=PROJ-123

# Save output to file
make run-output TICKET=PROJ-123

# Find PR with matching ticket
make find-pr TICKET=PROJ-123

# Update a specific PR
make update-pr TICKET=PROJ-123 PR=42
# Or find and update automatically
make update-pr TICKET=PROJ-123

# Batch update all PRs
make batch

# Batch update with prefix filter
make batch PREFIX=XY

# Dry run batch update
make batch-dry
```

## Deployment Options

### Kubernetes Deployment

Deploy using kubectl:

```bash
# Deploy everything (secrets, configmap, cronjob)
make k8s-deploy

# View deployment logs
make k8s-logs

# List recent jobs
make k8s-jobs

# Remove deployment
make k8s-delete
```

### Helm Deployment

Deploy using Helm:

```bash
# First, create your secrets file
cp k8s/helm/jira2pr-cronjob/secrets.yaml my-secrets.yaml
# Edit my-secrets.yaml with your credentials

# Install
make helm-install SECRETS_FILE=my-secrets.yaml

# Upgrade after changes
make helm-upgrade SECRETS_FILE=my-secrets.yaml

# Check status
make helm-status

# Uninstall
make helm-delete
```

### GitHub Actions

Trigger GitHub Actions workflow:

```bash
# Run workflow
make gh-run

# Run in dry-run mode
make gh-run-dry

# Check workflow status
make gh-status
```

## Development

```bash
# Run tests
make test

# Lint code
make lint

# Format code
make format

# Clean generated files
make clean
```

## Examples

### Example 1: Local Testing

```bash
# Set up environment
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_USERNAME="your.email@example.com"
export JIRA_API_TOKEN="your-token"
export GITHUB_TOKEN="ghp_..."
export GITHUB_OWNER="your-org"
export GITHUB_REPO="your-repo"

# Check environment
make check-env

# Test with a single ticket
make run TICKET=XY-123

# Test batch update in dry-run
make batch-dry
```

### Example 2: Deploy to Kubernetes

```bash
# Ensure .envrc file exists with your credentials
# Deploy
make k8s-deploy

# Monitor
make k8s-logs
make k8s-jobs
```

### Example 3: Deploy with Helm

```bash
# Create secrets file
cp k8s/helm/jira2pr-cronjob/secrets.yaml prod-secrets.yaml
# Edit prod-secrets.yaml

# Deploy
make helm-install SECRETS_FILE=prod-secrets.yaml

# Later, after code changes
make helm-upgrade SECRETS_FILE=prod-secrets.yaml
```

## Troubleshooting

### Environment Variables Not Set

If you get "not set" errors, ensure you've:
1. Created a `.envrc` file with your credentials
2. Loaded it with `source .envrc` or `direnv allow`

### Kubernetes Deployment Issues

```bash
# Check if secrets were created
kubectl get secret jira2pr-secrets

# Check if configmap was created
kubectl get configmap jira2pr-script

# Check cronjob status
kubectl describe cronjob jira2pr-batch-update
```

### No Logs Available

If `make k8s-logs` shows no logs, the cronjob may not have run yet. Check the schedule and manually trigger if needed:

```bash
kubectl create job --from=cronjob/jira2pr-batch-update test-run
```