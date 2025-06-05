#!/usr/bin/env python3
"""
Test cases for Jira ticket ID extraction from PR titles
"""
import pytest
from jira2pr import GitHubPR

def create_github_pr():
    """Create a GitHubPR instance with dummy values for testing"""
    return GitHubPR("dummy_token", "test_owner", "test_repo")

@pytest.mark.parametrize("title,expected_id,prefix,known_projects", [
    # Negative test cases (should not match any ticket ID)
    ("fix: no ticket here", None, None, None),
    ("chore: update dependencies", None, None, None),
    ("123: just a number", None, None, None),
    ("A-123: project key too short", None, None, None),  # Project key too short
    ("ABCD-123: project key too long", None, None, None),  # Project key too long
    ("ABC-: missing number", None, None, None),
    ("-123: missing project key", None, None, None),
    ("ABC-123-567: too many parts", None, None, None),  # Too many parts
    ("ABC-123-456: multiple dashes", None, None, None),  # Multiple dashes
    
    # Positive test cases (should match)
    ("fix(ABC-123): resolve memory leak", "ABC-123", None, None),
    ("fix(abc:123): resolve memory leak", "ABC-123", None, None),
    ("fix(abc: 123): resolve memory leak", "ABC-123", None, None),
    ("fix(abc 123): resolve memory leak", "ABC-123", None, None),
    ("fix(ABC 123): resolve memory leak", "ABC-123", None, None),
    ("feat(auth/XYZ-456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz:456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz: 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/XYZ-456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz:456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz: 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/XYZ-456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz:456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz: 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/xyz 456): add OAuth support", "XYZ-456", None, None),
    ("feat(auth/XYZ-456): add OAuth support", "XYZ-456", None, None),

    # Conventional commit with ticket after type
    ("fix: ABC-789 - handle edge case", "ABC-789", None, None),
    ("fix: ABC-789 handle edge case", "ABC-789", None, None),
    ("fix: abc:789 handle edge case", "ABC-789", None, None),
    ("fix: abc: 789 handle edge case", "ABC-789", None, None),
    ("fix: abc 789 handle edge case", "ABC-789", None, None),
    ("fix: abc:789 handle edge case", "ABC-789", None, None),
    ("fix: abc: 789 handle edge case", "ABC-789", None, None),
    ("fix: abc 789 handle edge case", "ABC-789", None, None),

    # Ticket ID at start
    ("ABC-123: Initial implementation", "ABC-123", None, None),
    ("ABC-123 Initial implementation", "ABC-123", None, None),
    ("abc:123 - Fix login issue", "ABC-123", None, None),
    ("ABC 123 - Fix login issue", "ABC-123", None, None),
    ("abc: 123 - Fix login issue", "ABC-123", None, None),

    # Ticket ID in brackets
    ("[ABC-123] Add new feature", "ABC-123", None, None),
    ("[abc-123] Add new feature", "ABC-123", None, None),
    ("[abc 123] Add new feature", "ABC-123", None, None),
    ("[abc:123] Add new feature", "ABC-123", None, None),
    ("[ABC 123] Add new feature", "ABC-123", None, None),
    ("[abc: 123] Add new feature", "ABC-123", None, None),

    # Ticket ID in description
    ("chore(deps): update dependencies (ABC-123)", "ABC-123", None, None),
    ("fix: resolve issue with login Fixes ABC-123", "ABC-123", None, None),

    # Multiple ticket IDs
    ("feat(ui)!: redesign dashboard [ABC-123, DEF-456]", "ABC-123", None, None),

    # With prefix filtering
    ("fix: ABC-123 - Fix login issue", "ABC-123", "ABC", None),
    ("fix: XYZ-123 - Fix login issue", None, "ABC", None),  # Should be filtered out by prefix
    ("fix: ABC123 - Fix login issue", "ABC-123", "ABC", None),
    ("fix: abc123 - Fix login issue", "ABC-123", "ABC", None),
    ("fix: abc-123 - Fix login issue", "ABC-123", "ABC", None),
    ("fix: abc 123 - Fix login issue", "ABC-123", "ABC", None),
    ("abc:123 - Fix login issue", "ABC-123", "ABC", None),
    ("ABC 123 - Fix login issue", "ABC-123", "ABC", None),
    ("abc: 123 - Fix login issue", "ABC-123", "ABC", None),
        # Test prefix filtering with partial matches
        ("fix: ABC-123 - Fix login issue", "ABC-123", "AB", None),  # Prefix is a substring of project key
        ("fix: AB-123 - Fix login issue", None, "ABC", None),   # Project key doesn't match prefix (AB != ABC)
        ("fix: ABC-123 - Fix login issue", None, "XYZ", None),  # No match for prefix
    
    # Test with known projects
    ("fix: ABC-123 - Fix login issue", "ABC-123", None, ["ABC"]),
    ("fix: XYZ-123 - Fix login issue", None, None, ["ABC"]),  # Not in known projects
    ("fix: ABC-123 - Fix login issue", None, None, ["XYZ"]),  # Not in known projects
    ("fix: ABC-123 - Fix login issue", "ABC-123", None, ["ABC", "XYZ"])  # In one of known projects
])
def test_extract_ticket_id_from_title(title, expected_id, prefix, known_projects):
    """Test extracting ticket IDs from various PR title formats"""
    pr = create_github_pr()
    result = pr.extract_ticket_ids_from_title(
        title, 
        prefix=prefix,
        known_projects=known_projects
    )
    assert result == expected_id, f"Expected {expected_id} but got {result} for title: {title}"

def test_extract_multiple_ticket_ids():
    """Test extracting multiple ticket IDs when first_only=False"""
    pr = create_github_pr()
    title = "feat(ui)!: redesign dashboard [ABC-123, DEF-456]"
    result = pr.extract_ticket_ids_from_title(title, first_only=False)
    assert len(result) == 2
    assert "ABC-123" in result
    assert "DEF-456" in result

def test_normalize_ticket_id():
    """Test ticket ID normalization"""
    from jira2pr import normalize_ticket_id

    test_cases = [
        ("abc123", "ABC-123"),
        ("ABC-123", "ABC-123"),
        ("abc 123", "ABC-123"),
        ("abc-123", "ABC-123"),
        ("ABC 123", "ABC-123"),
    ]

    for input_id, expected in test_cases:
        result = normalize_ticket_id(input_id)
        assert result == expected, f"Expected {expected} but got {result} for input {input_id}"

def test_ticket_id_with_known_projects():
    """Test filtering by known projects"""
    pr = create_github_pr()
    title = "fix: ABC-123 - Fix login issue"

    # Should match when project is in known_projects
    result = pr.extract_ticket_ids_from_title(title, known_projects=["ABC"])
    assert result == "ABC-123"

    # Should not match when project is not in known_projects
    result = pr.extract_ticket_ids_from_title(title, known_projects=["XYZ"])
    assert result is None

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
