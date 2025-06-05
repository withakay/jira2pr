#!/usr/bin/env python3
"""
Script to fetch Jira ticket description and format it for PR description or update GitHub PR
"""

import os
import sys
import requests
import argparse
from urllib.parse import urljoin
import json
import base64
import re
from typing import Optional, List, Set, Union, Tuple


def normalize_ticket_id(ticket_id):
    """
    Normalize a Jira ticket ID to a standard format

    Args:
        ticket_id: Jira ticket ID in various formats (e.g., XY-100, Xy100, xy 100)

    Returns:
        str: Normalized ticket ID (e.g., XY-100)
    """
    # Remove spaces and convert to uppercase
    ticket_id = ticket_id.upper().replace(" ", "")

    # Check if the ticket ID already has a hyphen
    if "-" in ticket_id:
        return ticket_id

    # Extract project key and number using regex
    match = re.match(r'^([A-Z]+)[-]?([0-9]+)$', ticket_id)
    if match:
        project, number = match.groups()
        return f"{project}-{number}"

    return ticket_id


class GitHubPR:
    def __init__(self, token, owner, repo):
        """
        Initialize the GitHub PR client

        Args:
            token: GitHub personal access token
            owner: GitHub repository owner/organization
            repo: GitHub repository name
        """
        self.base_url = "https://api.github.com"
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def get_pr_description(self, pr_number):
        """
        Get the current description of a PR

        Args:
            pr_number: GitHub PR number

        Returns:
            str: Current PR description
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get('body', '')
        except requests.exceptions.RequestException as e:
            print(f"Error fetching PR description: {e}")
            sys.exit(1)

    def _ticket_info_exists_in_description(self, description, ticket_id, jira_base_url=None):
        """
        Check if the ticket information already exists in the description

        Args:
            description: The PR description to check
            ticket_id: Jira ticket ID to look for
            jira_base_url: Optional base URL of the Jira instance

        Returns:
            bool: True if ticket info is found, False otherwise
        """
        if not description or not ticket_id:
            return False

        normalized_id = normalize_ticket_id(ticket_id)
        patterns = []

        # Check for Jira ticket URL in the description if base URL is provided
        if jira_base_url:
            jira_base_url = jira_base_url.rstrip('/')
            ticket_url_pattern = fr"{re.escape(jira_base_url)}/browse/{re.escape(normalized_id)}"
            patterns.append(ticket_url_pattern)
        else:
            # Check for ticket ID patterns in description
            patterns.extend([
                fr'\[{re.escape(normalized_id)}\]',  # [XY-123]
                fr'\*\*{re.escape(normalized_id)}\*\*',  # **XY-123**
                fr'\*\*\[{re.escape(normalized_id)}\]\*\*',  # **[XY-123]**
                f'Jira.*{re.escape(normalized_id)}',  # Jira ticket XY-123
                f"{normalized_id.split('-')[0]}-{normalized_id.split('-')[1]}"  # XY-123
            ])


        for pattern in patterns:
            if re.search(pattern, description, re.IGNORECASE):
                return True
        return False

    def update_pr_description(self, pr_number, description, append=True, ticket_id=None, jira_base_url=None):
        """
        Update the description of a PR

        Args:
            pr_number: GitHub PR number
            description: New description content
            append: If True, append to existing description; otherwise replace
            ticket_id: Jira ticket ID to check if already in description
            jira_base_url: Base URL of the Jira instance to check for ticket URLs

        Returns:
            bool: True if successful, False otherwise
            str: Status message indicating what happened
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls/{pr_number}"
        current_description = self.get_pr_description(pr_number)

        # Check if ticket info already exists in the description
        if ticket_id and current_description and self._ticket_info_exists_in_description(
            current_description, ticket_id, jira_base_url
        ):
            return True, "PR description already contains Jira ticket information or URL"

        # If we get here, the ticket info is not in the description or we're not checking
        if append and current_description:
            description = f"{current_description}\n\n{description}"

        data = {"body": description}

        try:
            response = requests.patch(url, headers=self.headers, json=data)
            response.raise_for_status()
            return True, "PR description updated successfully"
        except requests.exceptions.RequestException as e:
            error_msg = f"Error updating PR description: {e}"
            print(error_msg)
            return False, error_msg

    def list_pull_requests(self, state="open"):
        """
        List pull requests in the repository

        Args:
            state: PR state (open, closed, all)

        Returns:
            list: List of pull request data
        """
        url = f"{self.base_url}/repos/{self.owner}/{self.repo}/pulls"
        params = {"state": state, "per_page": 100}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error listing pull requests: {e}")
            return []

    def find_pr_by_ticket_id(self, ticket_id):
        """
        Find a pull request that matches a Jira ticket ID

        Args:
            ticket_id: Jira ticket ID

        Returns:
            dict: Pull request data if found, None otherwise
        """
        # Normalize the ticket ID
        normalized_id = normalize_ticket_id(ticket_id)

        # Get all open PRs
        pull_requests = self.list_pull_requests()

        # Create regex patterns for different formats
        # Match at the start of the title with optional space/dash after the project key
        pattern = re.compile(f"^{normalized_id.split(
            '-')[0]}[-\\s]?{normalized_id.split('-')[1]}", re.IGNORECASE)

        for pr in pull_requests:
            title = pr.get("title", "")
            if pattern.match(title):
                return pr

        return None

    def extract_ticket_ids_from_title(
        self,
        title: str,
        prefix: Optional[str] = None,
        known_projects: Optional[Union[Set[str], List[str]]] = None,
        first_only: bool = True
    ) -> Union[Optional[str], List[str]]:
        """
        Extract JIRA ticket IDs from PR title following conventional commit patterns

        Args:
            title: PR title to extract from
            prefix: Optional ticket prefix filter
            known_projects: Optional set/list of known JIRA project keys
            first_only: If True, return first match only; if False, return all matches

        Returns:
            str or list: First ticket ID, None if not found (when first_only=True)
                        List of ticket IDs (when first_only=False)
        """
        if not title:
            return None if first_only else []

        # Convert known_projects to uppercase set for faster lookup
        if known_projects:
            known_projects = {p.upper() for p in known_projects}

        found_tickets = []

        # Define pattern groups for better organization
        COMMIT_TYPES = r'(?:feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert|deploy|deployment|deployed)'

        # Project key: 2-3 uppercase letters, case insensitive
        PROJECT_KEY = r'([A-Za-z]{2,3})'

        # Ticket number: 1-6 digits
        TICKET_NUMBER = r'(\d{1,6})'

        # Separators: hyphen, space, colon, or nothing
        SEPARATOR = r'[-\s:]?'

        # Optional space
        OPTIONAL_SPACE = r'\s*'

        # Base pattern that matches project + number with any separator
        # This pattern uses lookahead to ensure we match the full project key
        TICKET_PATTERN = fr'(?<![A-Za-z])({PROJECT_KEY}){SEPARATOR}{OPTIONAL_SPACE}({TICKET_NUMBER})(?![\d-])'

        ACTION_WORDS = r'(?:fixes?|closes?|resolves?|refs?|references?|see|re|jira|ticket)'

        # Pattern definitions with names for debugging
        pattern_definitions = [
            # 1. Conventional commit with ticket after type (e.g., "fix: MK-123 Description")
            ('conv_type_ticket', fr'^{COMMIT_TYPES}:\s+{TICKET_PATTERN}'),

            # 2. Conventional commit with ticket in scope (e.g., "fix(MK-123): description")
            ('conv_scope', fr'^{COMMIT_TYPES}\(([^)]*{TICKET_PATTERN}[^)]*)\)!?:\s*'),

            # 3. Conventional commit with ticket in brackets after type (e.g., "fix: [MK-123] Description")
            ('conv_type_brackets', fr'^{COMMIT_TYPES}:\s+\[\s*{TICKET_PATTERN}\s*\]'),

            # 4. Ticket ID with colon (e.g., "MK-123: Description")
            ('ticket_colon', fr'{TICKET_PATTERN}'),

            # 5. Standard patterns (ticket at start of line)
            ('start_simple', fr'^{TICKET_PATTERN}[\s:\-]'),

            # 6. Ticket ID in brackets (e.g., "[MK-123] Description")
            ('ticket_brackets', fr'\[\s*{TICKET_PATTERN}\s*\]'),

            # 7. Action word patterns (e.g., "fixes MK-123")
            ('action_word', fr'{ACTION_WORDS}\s*:?\s*{TICKET_PATTERN}'),

            # 8. Ticket ID by itself (as a last resort)
            ('ticket_only', fr'{TICKET_PATTERN}'),
        ]

        # Process each pattern
        for pattern_name, pattern in pattern_definitions:
            try:
                matches = re.finditer(pattern, title, re.IGNORECASE)

                for match in matches:
                    try:
                        # The pattern now has multiple groups for project and number
                        # Group 1: Full match (if captured)
                        # Group 2: Project key
                        # Group 3: Ticket number

                        # Find which groups were actually captured
                        groups = match.groups()
                        project_key = None
                        ticket_number = None

                        # Find the project key and ticket number in the groups
                        for i, group in enumerate(groups):
                            if not group:
                                continue

                            # Check if this looks like a project key (2-3 letters)
                            if re.match(r'^[A-Za-z]{2,3}$', group, re.IGNORECASE):
                                project_key = group.upper()
                                # The next non-None group should be the ticket number
                                for j in range(i+1, len(groups)):
                                    if groups[j] and groups[j].isdigit():
                                        ticket_number = groups[j]
                                        break
                                break

                        if not project_key or not ticket_number:
                            print(f"  Could not extract project key or ticket number from match for pattern '{pattern_name}'")
                            continue

                        # Construct the ticket ID
                        ticket_id = f"{project_key}-{ticket_number}"
                        print(f"  Matched '{pattern_name}' pattern with ticket ID: {ticket_id}")

                        # Apply filters
                        if prefix and not project_key.startswith(prefix.upper()):
                            print(f"  Project key {project_key} does not match prefix {prefix}")
                            continue

                        if known_projects and project_key not in known_projects:
                            print(f"  Project key {project_key} not in known projects")
                            continue

                        if ticket_id not in found_tickets:
                            found_tickets.append(ticket_id)
                            if first_only:
                                return ticket_id

                    except Exception as e:
                        print(f"  Error extracting ticket ID from match: {e}")
                        continue

            except re.error:
                # Skip invalid patterns
                continue

        if first_only:
            return found_tickets[0] if found_tickets else None
        return found_tickets

    def batch_update_prs(self, jira_formatter, prefix=None, dry_run=False):
        """
        Batch update PRs by extracting ticket IDs from titles and updating descriptions

        Args:
            jira_formatter: JiraPRFormatter instance to get ticket info
            prefix: Optional ticket prefix to match
            dry_run: If True, don't actually update PRs

        Returns:
            dict: Summary of updates (total, updated, skipped, failed)
        """
        # Get all open PRs
        print(f"Fetching open PRs from {self.owner}/{self.repo}...")
        pull_requests = self.list_pull_requests("open")

        if not pull_requests:
            print("No open PRs found.")
            return {"total": 0, "updated": 0, "skipped": 0, "failed": 0}

        print(f"Found {len(pull_requests)} open PRs.")

        # Track statistics
        stats = {"total": len(pull_requests), "updated": 0,
                 "skipped": 0, "failed": 0}

        # Process each PR
        for pr in pull_requests:
            pr_number = pr.get("number")
            pr_title = pr.get("title", "")

            print(f"\nProcessing PR #{pr_number}: {pr_title}")

            # Extract ticket ID from title
            ticket_id = self.extract_ticket_ids_from_title(pr_title, prefix)

            if not ticket_id:
                print(f"  ⚠️ No ticket ID found in PR title. Skipping.")
                stats["skipped"] += 1
                continue

            print(f"  Found ticket ID: {ticket_id}")

            # Check if the PR description already contains the Jira ticket information
            current_description = self.get_pr_description(pr_number)
            should_update = True

            if current_description:
                jira_base_url = getattr(jira_formatter, 'jira_url', None)
                if self._ticket_info_exists_in_description(current_description, ticket_id, jira_base_url):
                    print(f"  ℹ️ PR #{pr_number} already contains Jira ticket information. Skipping.")
                    should_update = False
                    stats["skipped"] += 1

            if should_update:
                try:
                    # Fetch ticket information
                    print(f"  Fetching Jira ticket: {ticket_id}")
                    ticket_info = jira_formatter.get_ticket_info(ticket_id)

                    # Generate PR description
                    pr_description = jira_formatter.format_description_for_pr(ticket_info)

                    if dry_run:
                        print(f"  [DRY RUN] Would update PR #{pr_number} with ticket {ticket_id} information")
                        stats["updated"] += 1
                    else:
                        # Update PR with the Jira URL for checking
                        success, message = self.update_pr_description(
                            pr_number=pr_number,
                            description=pr_description,
                            append=True,
                            ticket_id=ticket_id,
                            jira_base_url=jira_formatter.jira_url if hasattr(jira_formatter, 'jira_url') else None
                        )

                        if success:
                            print(f"  ✅ {message}")
                            stats["updated"] += 1
                        else:
                            print(f"  ⚠️ {message}")
                            stats["skipped"] += 1

                except Exception as e:
                    print(f"  ❌ Error updating PR #{pr_number}: {e}")
                    stats["failed"] += 1

        return stats


class JiraPRFormatter:
    def __init__(self, jira_url, username, api_token):
        """
        Initialize the Jira client

        Args:
            jira_url: Base URL of your Jira instance (e.g., https://yourcompany.atlassian.net)
            username: Your Jira username/email
            api_token: Your Jira API token
        """
        self.jira_url = jira_url.rstrip('/')
        self.auth = (username, api_token)

    def get_ticket_info(self, ticket_id):
        """
        Fetch ticket information from Jira

        Args:
            ticket_id: Jira ticket ID (e.g., PROJ-123)

        Returns:
            dict: Ticket information including summary, description, etc.
        """
        url = f"{self.jira_url}/rest/api/3/issue/{ticket_id}"

        try:
            response = requests.get(url, auth=self.auth)
            response.raise_for_status()

            issue_data = response.json()

            return {
                'key': issue_data['key'],
                'summary': issue_data['fields']['summary'],
                'description': issue_data['fields'].get('description', ''),
                'status': issue_data['fields']['status']['name'],
                'priority': issue_data['fields']['priority']['name'],
                'assignee': issue_data['fields']['assignee']['displayName'] if issue_data['fields']['assignee'] else 'Unassigned',
                'url': f"{self.jira_url}/browse/{issue_data['key']}"
            }

        except requests.exceptions.RequestException as e:
            print(f"Error fetching Jira ticket: {e}")
            sys.exit(1)
        except KeyError as e:
            print(f"Error parsing Jira response - missing field: {e}")
            sys.exit(1)

    def format_description_for_pr(self, ticket_info, include_details=True):
        """
        Format the ticket information for PR description

        Args:
            ticket_info: Dictionary containing ticket information
            include_details: Whether to include additional details like status, priority

        Returns:
            str: Formatted PR description
        """
        pr_description = "### ---- 🤖 TicketBot 🤖 ----\n"
        pr_description += "#### 🎫 Ticket\n"
        pr_description += f"[{ticket_info['key']
                              }]({ticket_info['url']}) - {ticket_info['summary']}\n\n"

        if ticket_info['description']:
            # Handle different description formats (plain text vs Atlassian Document Format)
            description = self._extract_description_text(
                ticket_info['description'])
            if description.strip():
                pr_description += f"#### 📝 Description\n\n{description}\n\n"

        # if include_details:
        #     pr_description += f"**Status:** {ticket_info['status']}  \n"
        #     pr_description += f"**Priority:** {ticket_info['priority']}  \n"
        #     pr_description += f"**Assignee:** {ticket_info['assignee']}\n\n"

        # pr_description += "---\n\n"
        # pr_description += "## 🔄 Changes Made\n\n"
        # pr_description += "<!-- Please describe the changes you've made -->\n\n"
        # pr_description += "## ✅ Testing\n\n"
        # pr_description += "<!-- Describe how you tested your changes -->\n\n"
        # pr_description += "## 📸 Screenshots (if applicable)\n\n"
        # pr_description += "<!-- Add screenshots here if relevant -->\n"

        return pr_description

    def _extract_description_text(self, description):
        """
        Extract text from Jira description (handles both plain text and ADF format)

        Args:
            description: Description field from Jira (can be string or dict)

        Returns:
            str: Plain text description
        """
        if isinstance(description, str):
            return description
        elif isinstance(description, dict):
            # Handle Atlassian Document Format (ADF)
            return self._extract_text_from_adf(description)
        else:
            return str(description) if description else ""

    def _extract_text_from_adf(self, adf_content):
        """
        Extract plain text from Atlassian Document Format

        Args:
            adf_content: ADF content dictionary

        Returns:
            str: Extracted plain text
        """
        def extract_text(node):
            if isinstance(node, dict):
                if node.get('type') == 'text':
                    return node.get('text', '')
                elif 'content' in node:
                    return ''.join(extract_text(child) for child in node['content'])
                else:
                    return ''
            elif isinstance(node, list):
                return ''.join(extract_text(item) for item in node)
            else:
                return str(node) if node else ""

        return extract_text(adf_content)


def main():
    parser = argparse.ArgumentParser(
        description='Generate PR description from Jira ticket and optionally update GitHub PR')
    parser.add_argument(
        'ticket_id', help='Jira ticket ID (e.g., PROJ-123)', nargs='?')

    # Jira arguments
    jira_group = parser.add_argument_group('Jira Options')
    jira_group.add_argument('--jira-url', help='Jira base URL',
                            default=os.getenv('JIRA_URL'))
    jira_group.add_argument('--username', help='Jira username/email',
                            default=os.getenv('JIRA_USERNAME'))
    jira_group.add_argument('--api-token', help='Jira API token',
                            default=os.getenv('JIRA_API_TOKEN'))
    jira_group.add_argument('--simple', action='store_true',
                            help='Simple format without extra details')

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--output', '-o', help='Output file path (optional)')

    # GitHub PR options
    github_group = parser.add_argument_group('GitHub PR Options')
    github_group.add_argument('--update-pr', type=int, nargs='?', const=True,
                              help='GitHub PR number to update. If used without a number, automatically enables PR finding and updates the found PR')
    github_group.add_argument('--find-pr', action='store_true',
                              help='Find PR with title matching the Jira ticket ID')
    github_group.add_argument('--batch-update', action='store_true',
                              help='Batch update all open PRs by extracting ticket IDs from PR titles')
    github_group.add_argument('--ticket-prefix',
                              help='Jira ticket prefix to match in PR titles (e.g., XY, ABC)',
                              default=os.getenv('JIRA_TICKET_PREFIX'))
    github_group.add_argument('--dry-run', action='store_true',
                              help='Show what would be updated without making changes')
    github_group.add_argument('--github-token', help='GitHub personal access token',
                              default=os.getenv('GITHUB_TOKEN'))
    github_group.add_argument('--github-owner', help='GitHub repository owner/organization',
                              default=os.getenv('GITHUB_OWNER'))
    github_group.add_argument('--github-repo', help='GitHub repository name',
                              default=os.getenv('GITHUB_REPO'))
    github_group.add_argument('--replace', action='store_true',
                              help='Replace PR description instead of appending')

    args = parser.parse_args()

    # Check if batch update is requested
    if args.batch_update:
        # Validate GitHub parameters for batch update
        if not args.github_token:
            print(
                "Error: GitHub token is required. Set GITHUB_TOKEN environment variable or use --github-token")
            sys.exit(1)

        if not args.github_owner:
            print(
                "Error: GitHub owner is required. Set GITHUB_OWNER environment variable or use --github-owner")
            sys.exit(1)

        if not args.github_repo:
            print(
                "Error: GitHub repo is required. Set GITHUB_REPO environment variable or use --github-repo")
            sys.exit(1)

        # Validate Jira parameters for batch update
        if not args.jira_url:
            print(
                "Error: Jira URL is required. Set JIRA_URL environment variable or use --jira-url")
            sys.exit(1)

        if not args.username:
            print(
                "Error: Username is required. Set JIRA_USERNAME environment variable or use --username")
            sys.exit(1)

        if not args.api_token:
            print(
                "Error: API token is required. Set JIRA_API_TOKEN environment variable or use --api-token")
            sys.exit(1)

        # Initialize clients
        formatter = JiraPRFormatter(
            args.jira_url, args.username, args.api_token)
        github_pr = GitHubPR(
            args.github_token, args.github_owner, args.github_repo)

        # Run batch update
        print(f"\nBatch updating PRs in {
              args.github_owner}/{args.github_repo}")
        if args.dry_run:
            print("[DRY RUN] No changes will be made")

        if args.ticket_prefix:
            print(f"Using ticket prefix: {args.ticket_prefix}")

        stats = github_pr.batch_update_prs(
            formatter,
            prefix=args.ticket_prefix,
            dry_run=args.dry_run
        )

        print(f"\nBatch update complete:")
        print(f"  Total PRs: {stats['total']}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Failed: {stats['failed']}")

        # Exit after batch update
        sys.exit(0)

    # For non-batch operations, ticket_id is required
    if not args.ticket_id:
        print("Error: Jira ticket ID is required unless using --batch-update")
        sys.exit(1)

    # Validate required parameters
    if not args.jira_url:
        print("Error: Jira URL is required. Set JIRA_URL environment variable or use --jira-url")
        sys.exit(1)

    if not args.username:
        print("Error: Username is required. Set JIRA_USERNAME environment variable or use --username")
        sys.exit(1)

    if not args.api_token:
        print("Error: API token is required. Set JIRA_API_TOKEN environment variable or use --api-token")
        sys.exit(1)

    # Initialize Jira formatter
    formatter = JiraPRFormatter(args.jira_url, args.username, args.api_token)

    # Fetch ticket information
    print(f"Fetching Jira ticket: {args.ticket_id}")
    ticket_info = formatter.get_ticket_info(args.ticket_id)

    # Handle GitHub operations if requested
    found_pr = None

    # If --update-pr is used without a value, enable PR finding automatically
    if args.update_pr is True:
        args.find_pr = True

    if args.find_pr or args.update_pr:
        # Validate GitHub parameters
        if not args.github_token:
            print(
                "Error: GitHub token is required. Set GITHUB_TOKEN environment variable or use --github-token")
            sys.exit(1)

        if not args.github_owner:
            print(
                "Error: GitHub owner is required. Set GITHUB_OWNER environment variable or use --github-owner")
            sys.exit(1)

        if not args.github_repo:
            print(
                "Error: GitHub repo is required. Set GITHUB_REPO environment variable or use --github-repo")
            sys.exit(1)

        # Initialize GitHub PR client
        github_pr = GitHubPR(
            args.github_token, args.github_owner, args.github_repo)

        # Find PR by ticket ID if requested - do this BEFORE generating description
        if args.find_pr:
            print(f"Searching for PR matching Jira ticket {args.ticket_id}...")
            found_pr = github_pr.find_pr_by_ticket_id(args.ticket_id)

            if found_pr:
                pr_number = found_pr.get("number")
                pr_title = found_pr.get("title")
                pr_url = found_pr.get("html_url")
                print(f"\u2705 Found matching PR: #{pr_number} - {pr_title}")
                print(f"PR URL: {pr_url}")

                # If update_pr was provided as a flag without value, use the found PR number
                if args.update_pr is True:
                    args.update_pr = pr_number
                    print(f"Will update PR #{pr_number} if needed")
            else:
                print(f"\u274c No PR found matching ticket {args.ticket_id}")
                if args.update_pr is True:
                    print("No PR to update. Use --update-pr with a specific PR number.")
                    sys.exit(1)

    # Determine if we need to generate the description
    # Only generate if we're saving to file or updating a PR
    # Don't generate if we're just finding a PR
    need_description = args.output or isinstance(args.update_pr, int)

    # Generate PR description if needed
    if need_description:
        pr_description = formatter.format_description_for_pr(
            ticket_info,
            include_details=not args.simple
        )

        # Output the result if requested (file output)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(pr_description)
            print(f"PR description saved to: {args.output}")

        # Update PR if requested
        if isinstance(args.update_pr, int):
            print(f"Checking PR #{args.update_pr}...")

            # First check if PR already contains the ticket information
            # Get current PR description
            current_description = github_pr.get_pr_description(args.update_pr)
            should_update = True

            # Check if PR already contains the ticket information
            if current_description and args.ticket_id:
                jira_base_url = getattr(args, 'jira_url', None)
                if github_pr._ticket_info_exists_in_description(current_description, args.ticket_id, jira_base_url):
                    print(f"PR #{args.update_pr} already contains Jira ticket information. No changes needed.")
                    sys.exit(0)

    if not args.github_repo:
        print("Error: GitHub repo is required. Set GITHUB_REPO environment variable or use --github-repo")
        sys.exit(1)


    # Only if we need to update, show the description and update the PR
    if should_update:
        # Show the description that will be used for the update
        print("\n" + "="*50)
        print("PR DESCRIPTION")
        print("="*50)
        print(pr_description)

        print(f"\nUpdating GitHub PR #{args.update_pr}...")
        data = {"body": pr_description}
        if args.replace is False and current_description:  # Append mode
            data = {"body": f"{current_description}\n\n{pr_description}"}

        url = f"{github_pr.base_url}/repos/{github_pr.owner}/{github_pr.repo}/pulls/{args.update_pr}"
        try:
            response = requests.patch(
                url, headers=github_pr.headers, json=data)
            response.raise_for_status()
            print(f"\u2705 Successfully updated PR #{args.update_pr}")
        except requests.exceptions.RequestException as e:
            error_msg = f"Error updating PR description: {e}"
            print(f"\u274c Failed to update PR #{args.update_pr}: {error_msg}")
            sys.exit(1)

    # Final success message
    if args.find_pr and not need_description:
        print(f"\n\u2705 Successfully processed Jira ticket {
              ticket_info['key']}")
    else:
        print(f"\n\u2705 Successfully generated PR description for {
              ticket_info['key']}")


if __name__ == "__main__":
    main()
