# Files Directory

This directory contains files that are included in the Helm chart.

## Symbolic Links

The following files are symbolic links to the main project files:

- `jira2pr.py` → `../../../../jira2pr/jira2pr.py`
- `pyproject.toml` → `../../../../jira2pr/pyproject.toml`
- `uv.lock` → `../../../../jira2pr/uv.lock`

This ensures that the Helm chart always uses the latest version of the script and its dependencies without needing to manually copy updates.

**Note:** When packaging this Helm chart for distribution, the symlinks should be replaced with the actual file contents.