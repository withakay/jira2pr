# Jira to PR Description Tool

A utility script that fetches Jira ticket information and formats it for GitHub PR descriptions. It can also directly update GitHub PR descriptions.

## Features

- Fetch Jira ticket information using the Jira API
- Format ticket details into a structured PR description
- Output to console or file
- Find GitHub PRs with titles matching a Jira ticket ID
- Update GitHub PR descriptions directly (append or replace)
- Skip updates for PRs that already contain Jira ticket information
- Batch update all open PRs by extracting ticket IDs from PR titles

## Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) - Fast Python package installer and resolver
- `requests` library

## Quick Start

A Makefile is provided for common operations. Run `make help` to see all available commands.

```bash
# Install dependencies
make install

# Run for a specific ticket
make run TICKET=PROJ-123

# Run batch update
make batch

# Deploy to Kubernetes
make k8s-deploy
```

See [docs/MAKEFILE.md](docs/MAKEFILE.md) for detailed usage.

## Manual Setup

1. Install uv (if not already installed):

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

2. Install dependencies:

```bash
cd jira2pr
uv sync
```

3. Set up environment variables (optional):

```bash
# Jira credentials
export JIRA_URL="https://your-company.atlassian.net"
export JIRA_USERNAME="your-email@example.com"
export JIRA_API_TOKEN="your-jira-api-token"

# GitHub credentials (for PR update feature)
export GITHUB_TOKEN="your-github-personal-access-token"
export GITHUB_OWNER="your-github-username-or-org"
export GITHUB_REPO="your-repo-name"
```

## Usage

### Basic Usage

```bash
# Generate PR description for Jira ticket PROJ-123
cd jira2pr
uv run python jira2pr.py PROJ-123
```

### Save to File

```bash
# Save PR description to a file
cd jira2pr
uv run python jira2pr.py PROJ-123 --output pr-description.md
```

### Find and Update GitHub PR

```bash
# Find PR with title matching Jira ticket PROJ-123
cd jira2pr
uv run python jira2pr.py PROJ-123 --find-pr

# Find PR with title matching Jira ticket PROJ-123 and update its description
uv run python jira2pr.py PROJ-123 --update-pr

# Update GitHub PR #42 with Jira ticket PROJ-123 information (append mode)
# Note: No changes will be made if PR already contains Jira ticket information
uv run python jira2pr.py PROJ-123 --update-pr 42

# Replace PR description instead of appending
uv run python jira2pr.py PROJ-123 --update-pr 42 --replace

# Batch update all open PRs by extracting ticket IDs from PR titles
uv run python jira2pr.py --batch-update

# Batch update with a specific ticket prefix (e.g., only PRs with 'XY-123' format)
uv run python jira2pr.py --batch-update --ticket-prefix XY

# Dry run to see what would be updated without making changes
uv run python jira2pr.py --batch-update --dry-run
```

## Command Line Options

### Jira Options

- `--jira-url`: Jira base URL (default: from JIRA_URL env var)
- `--username`: Jira username/email (default: from JIRA_USERNAME env var)
- `--api-token`: Jira API token (default: from JIRA_API_TOKEN env var)
- `--simple`: Use simple format without extra details

### Output Options

- `--output`, `-o`: Output file path

### GitHub PR Options

- `--find-pr`: Find PR with title matching the Jira ticket ID (only displays the PR, doesn't update it)
- `--update-pr [PR_NUMBER]`: GitHub PR number to update. If used without a number, automatically enables PR finding and updates the found PR
- `--batch-update`: Batch update all open PRs by extracting ticket IDs from PR titles
- `--ticket-prefix PREFIX`: Jira ticket prefix to match in PR titles (e.g., XY, ABC) (default: from JIRA_TICKET_PREFIX env var)
- `--dry-run`: Show what would be updated without making changes
- `--github-token`: GitHub personal access token (default: from GITHUB_TOKEN env var)
- `--github-owner`: GitHub repository owner/organization (default: from GITHUB_OWNER env var)
- `--github-repo`: GitHub repository name (default: from GITHUB_REPO env var)
- `--replace`: Replace PR description instead of appending

## Example Output

```markdown
### ---- 🤖 TicketBot 🤖 ----
#### 🎫 Ticket
[PROJ-123](https://your-company.atlassian.net/browse/PROJ-123) - Implement new feature

#### 📝 Description

This is the description from the Jira ticket.

```

## GitHub Action

This tool can be run automatically using GitHub Actions. See [.github/workflows/README.md](.github/workflows/README.md) for setup instructions.

### Quick Setup

1. Add repository variables in Settings → Secrets and variables → Actions → Variables:
   - `JIRA_URL`: Your Jira instance URL
   - `JIRA_USERNAME`: Your Jira username/email
   - `JIRA_TICKET_PREFIX` (optional): Default ticket prefix

2. Add repository secret in Settings → Secrets and variables → Actions → Secrets:
   - `JIRA_API_TOKEN`: Your Jira API token

3. The action will run automatically every hour or can be triggered manually from the Actions tab.

## Security Notes

- Store your Jira API token and GitHub token securely
- Consider using environment variables instead of command line arguments for sensitive information
