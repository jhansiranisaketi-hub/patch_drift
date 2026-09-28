"""
pr_generator.py — PatchDrift PR Generator

Generates a GitHub Pull Request with the permanent code fix for an API migration.

After runtime healing, PatchDrift can generate a source-code patch and open a PR
so the temporary adapter becomes a permanent fix in the application codebase.
"""

from __future__ import annotations

import os
from typing import Any


# ---------------------------------------------------------------------------
# Generate PR Diff (hardcoded for MVP demo)
# ---------------------------------------------------------------------------

def generate_pr_diff() -> dict[str, Any]:
    """
    Generate a Pull Request diff showing the permanent code fix.

    For the MVP, this returns a hardcoded example showing the
    billing_address → customer.address.billing migration.

    In production, this would:
    1. Parse the application source code
    2. Find where the old API call is made
    3. Generate the transformation
    4. Create a branch
    5. Commit the change
    6. Open a PR via GitHub API

    Returns:
        Dictionary with PR metadata and code diff

    Example:
        pr = generate_pr_diff()
        print(pr["title"])
        print(pr["before"])
        print(pr["after"])
    """
    return {
        "title": "fix: migrate billing_address to customer.address.billing",
        "branch": "patchdrift/fix-billing-address-migration",
        "description": (
            "PatchDrift detected that the Payment API V2 no longer accepts "
            "the `billing_address` field in the flat format. The field has been "
            "moved to a nested structure at `customer.address.billing`.\n\n"
            "This PR updates the request payload to match the new API schema.\n\n"
            "**What changed:**\n"
            "- Old: `billing_address: address`\n"
            "- New: `customer.address.billing: address`\n\n"
            "**Verification:**\n"
            "- ✅ Adapter tested in sandbox against mock V2\n"
            "- ✅ Runtime healing successful\n"
            "- ✅ Migration stored in Hindsight\n\n"
            "**Related:**\n"
            "- API: Payment API V2\n"
            "- Error: `Unknown field: billing_address`\n"
            "- Healed: Yes\n"
        ),
        "before": (
            "const payment = {\n"
            "    customer_id: customerId,\n"
            "    billing_address: address\n"
            "};"
        ),
        "after": (
            "const payment = {\n"
            "    customer_id: customerId,\n"
            "    customer: {\n"
            "        address: {\n"
            "            billing: address\n"
            "        }\n"
            "    }\n"
            "};"
        ),
        "status": "ready",
        "labels": ["patchdrift", "api-migration", "auto-generated"],
    }


# ---------------------------------------------------------------------------
# Create GitHub PR (optional — requires token and repo)
# ---------------------------------------------------------------------------

def create_github_pr(
    repo_name: str,
    title: str,
    body: str,
    branch: str,
    base_branch: str = "main",
    token: str | None = None,
) -> dict[str, Any]:
    """
    Actually create a GitHub Pull Request.

    This is an optional extension if you want to open a real PR.

    Args:
        repo_name: GitHub repo in format "owner/repo"
        title: PR title
        body: PR description
        branch: Feature branch name
        base_branch: Target branch (default: main)
        token: GitHub personal access token (or env var GITHUB_TOKEN)

    Returns:
        Dictionary with PR URL and metadata

    Example:
        pr = create_github_pr(
            repo_name="myorg/myapp",
            title="fix: migrate billing_address",
            body="PatchDrift auto-generated migration",
            branch="patchdrift/fix-billing-address",
            token=os.getenv("GITHUB_TOKEN")
        )
        print(f"PR opened: {pr['url']}")
    """
    if token is None:
        token = os.getenv("GITHUB_TOKEN")

    if not token:
        return {
            "error": "GitHub token not provided. Set GITHUB_TOKEN env var or pass token parameter.",
            "status": "failed",
        }

    try:
        from github import Github

        g = Github(token)
        repo = g.get_repo(repo_name)

        # Create PR
        pr = repo.create_pull(
            title=title,
            body=body,
            head=branch,
            base=base_branch,
        )

        return {
            "status": "created",
            "url": pr.html_url,
            "number": pr.number,
            "title": pr.title,
        }

    except ImportError:
        return {
            "error": "PyGithub not installed. Install with: pip install PyGithub",
            "status": "failed",
        }
    except Exception as e:
        return {
            "error": f"Failed to create PR: {str(e)}",
            "status": "failed",
        }


# ---------------------------------------------------------------------------
# Generate code patch from adapter (future enhancement)
# ---------------------------------------------------------------------------

def generate_code_patch(
    source_file: str,
    adapter_map: dict,
    language: str = "python",
) -> str:
    """
    Generate a source code patch from an adapter mapping.

    This is a placeholder for future implementation that would:
    1. Parse the source file AST
    2. Find where the API call is made
    3. Transform the payload construction code
    4. Return a unified diff

    Args:
        source_file: Path to source file
        adapter_map: Field mapping dict
        language: Programming language

    Returns:
        Unified diff string
    """
    # Future: use AST transformation, rope, or other refactoring tools
    return "# Placeholder for code patch generation"
