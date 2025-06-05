# GitHub Actions for Jira2PR

This directory contains GitHub Actions workflows for automatically updating pull requests with Jira ticket information.

## Workflow: Update PRs with Jira Info

The `jira2pr.yml` workflow automatically scans open pull requests and updates their descriptions with information from linked Jira tickets.

### Features

- **Scheduled Runs**: Automatically runs every hour
- **Manual Triggers**: Can be triggered manually from the Actions tab
- **Dry Run Mode**: Test the workflow without making changes
- **Prefix Filtering**: Optionally filter PRs by Jira ticket prefix

### Setup Instructions

#### 1. Configure Repository Variables

Go to your repository's Settings → Secrets and variables → Actions → Variables tab and add:

- `JIRA_URL`: Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)
- `JIRA_USERNAME`: Your Jira username/email
- `JIRA_TICKET_PREFIX` (optional): Default ticket prefix to match (e.g., `XY`, `ABC`)

#### 2. Configure Repository Secrets

Go to your repository's Settings → Secrets and variables → Actions → Secrets tab and add:

- `JIRA_API_TOKEN`: Your Jira API token
  - Generate from: https://id.atlassian.com/manage-profile/security/api-tokens
  - Must have read access to Jira issues

Note: `GITHUB_TOKEN` is automatically provided by GitHub Actions and doesn't need to be configured.

### Usage

#### Automatic Runs

The workflow runs automatically every hour and will:
1. Scan all open pull requests
2. Extract Jira ticket IDs from PR titles
3. Fetch ticket information from Jira
4. Update PR descriptions with ticket details
5. Skip PRs that already have Jira information

#### Manual Runs

1. Go to the Actions tab in your repository
2. Select "Update PRs with Jira Info" workflow
3. Click "Run workflow"
4. Optional parameters:
   - **Dry Run**: Check this to see what would be updated without making changes
   - **Ticket Prefix**: Enter a specific prefix to only update matching PRs

### Customization

#### Change Schedule

Edit the cron expression in `.github/workflows/jira2pr.yml`:

```yaml
on:
  schedule:
    - cron: '0 * * * *'  # Every hour
```

Common schedules:
- `'*/30 * * * *'` - Every 30 minutes
- `'0 */2 * * *'` - Every 2 hours
- `'0 9-17 * * 1-5'` - Every hour during business hours (Mon-Fri 9am-5pm UTC)

#### Permissions

The workflow requires:
- `contents: read` - To checkout the repository
- `pull-requests: write` - To update PR descriptions

#### Dependencies

The workflow uses `uv` for fast Python dependency management. Dependencies are cached automatically to speed up workflow runs.

### Troubleshooting

1. **Workflow not running**: Check that GitHub Actions are enabled for your repository
2. **Authentication errors**: Verify your Jira API token is valid and has proper permissions
3. **No PRs updated**: Check that PR titles contain valid Jira ticket IDs (e.g., `XY-123: Fix bug`)
4. **Rate limits**: If you have many PRs, consider reducing the schedule frequency

### Security Notes

- Jira API tokens are stored as encrypted secrets
- The workflow only has write access to pull requests, not code
- GitHub token permissions are scoped to the minimum required