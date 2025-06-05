# Jira2PR CronJob Helm Chart

This Helm chart deploys a CronJob that automatically updates GitHub Pull Requests with information from linked Jira tickets.

## Features

- Automatically scans open PRs in a GitHub repository
- Extracts Jira ticket IDs from PR titles
- Fetches ticket information from Jira
- Updates PR descriptions with ticket details
- Configurable namespace and cron schedule

## Prerequisites

- Kubernetes cluster
- Helm 3+
- GitHub Personal Access Token with repo permissions
- Jira API Token

## Installation

1. Clone this repository:

```bash
git clone <repository-url>
cd k8s/helm/jira2pr-cronjob
```

2. The Python script is automatically included in the chart via the `files/jira2pr.py` file. If you need to update the script, simply modify this file.

3. Create a copy of the secrets template:

```bash
cp secrets.yaml my-secrets.yaml
```

4. Edit `my-secrets.yaml` with your Jira and GitHub credentials:

```yaml
secrets:
  jiraUrl: "https://your-company.atlassian.net"
  jiraUsername: "your.email@example.com"
  jiraApiToken: "your-jira-api-token"
  githubToken: "your-github-personal-access-token"
  githubOwner: "your-github-org-or-username"
  githubRepo: "your-repo-name"
```

5. Install the chart:

```bash
helm install jira2pr-cronjob . -f values.yaml -f my-secrets.yaml
```

## Configuration

The following table lists the configurable parameters of the chart and their default values:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `namespace` | Namespace to deploy the cronjob | `default` |
| `cronSchedule` | Cron schedule for the job | `"0/2 * * * *"` (every 2 minutes) |
| `successfulJobsHistoryLimit` | Number of successful jobs to keep | `3` |
| `failedJobsHistoryLimit` | Number of failed jobs to keep | `3` |
| `concurrencyPolicy` | Concurrency policy | `Forbid` |
| `image.repository` | Container image repository | `python` |
| `image.tag` | Container image tag | `3.10-slim` |
| `image.pullPolicy` | Container image pull policy | `IfNotPresent` |
| `secretName` | Name of the secret containing credentials | `kestra-secrets` |
| `configMapName` | Name of the ConfigMap containing the script | `jira2pr-script` |
| `resources` | CPU/Memory resource requests/limits | See `values.yaml` |

## Usage

After installation, the CronJob will run according to the schedule defined in `values.yaml`. By default, it runs every 2 minutes.

The job will:
1. Fetch all open PRs from the configured GitHub repository
2. Extract Jira ticket IDs from PR titles
3. Fetch ticket information from Jira
4. Update PR descriptions with the ticket information

## Uninstallation

```bash
helm uninstall jira2pr-cronjob
```

## Customization

To customize the chart, modify the `values.yaml` file or provide your own values file:

```bash
helm install jira2pr-cronjob . -f my-values.yaml -f my-secrets.yaml
```
