"""
Example Data Providers with Parameters (T041)
Demonstrates @param decorator usage with data providers
"""

from bifrost import data_provider, param


@data_provider(
    name="get_github_repos",
    description="Get GitHub repositories for an organization (requires GitHub token)",
    category="github",
    cache_ttl_seconds=300
)
@param(
    "token",
    type="string",
    label="GitHub Personal Access Token",
    required=True,
    help_text="GitHub PAT with repo access"
)
@param(
    "org",
    type="string",
    label="GitHub Organization",
    required=False,
    default_value="",
    help_text="Organization name (leave empty for personal repos)"
)
async def get_github_repos(context, token: str, org: str = ""):
    """
    Example data provider that requires a GitHub token parameter.

    This is a mock implementation for testing purposes.
    In production, this would make real GitHub API calls.

    Args:
        context: ExecutionContext with organization and user info
        token: GitHub personal access token
        org: Optional GitHub organization name

    Returns:
        List of repository options with label/value format
    """
    # Mock implementation for testing
    # In production, you would use the token to call GitHub API:
    # headers = {"Authorization": f"Bearer {token}"}
    # response = requests.get(f"https://api.github.com/orgs/{org}/repos", headers=headers)

    # Return mock data based on inputs
    if org:
        return [
            {
                "label": f"{org}/repo-1",
                "value": f"{org}/repo-1",
                "metadata": {"stars": 42, "private": False}
            },
            {
                "label": f"{org}/repo-2",
                "value": f"{org}/repo-2",
                "metadata": {"stars": 15, "private": True}
            },
        ]
    else:
        return [
            {
                "label": "my-personal-repo",
                "value": "user/my-personal-repo",
                "metadata": {"stars": 5, "private": False}
            }
        ]


@data_provider(
    name="get_github_branches",
    description="Get branches for a GitHub repository",
    category="github",
    cache_ttl_seconds=180
)
@param(
    "token",
    type="string",
    label="GitHub Personal Access Token",
    required=True
)
@param(
    "repo",
    type="string",
    label="Repository (owner/name)",
    required=True,
    help_text="Format: owner/repository-name"
)
async def get_github_branches(context, token: str, repo: str):
    """
    Example data provider for getting repository branches.

    Args:
        context: ExecutionContext
        token: GitHub personal access token
        repo: Repository in format "owner/name"

    Returns:
        List of branch options
    """
    # Mock implementation
    return [
        {"label": "main", "value": "main", "metadata": {"protected": True}},
        {"label": "develop", "value": "develop", "metadata": {"protected": False}},
        {"label": "feature/new-ui", "value": "feature/new-ui",
            "metadata": {"protected": False}},
    ]


@data_provider(
    name="get_filtered_licenses",
    description="Get Microsoft 365 licenses with filtering",
    category="m365",
    cache_ttl_seconds=300
)
@param(
    "filter",
    type="string",
    label="Filter",
    required=False,
    default_value="all",
    help_text="Filter: 'all', 'available', or 'assigned'"
)
async def get_filtered_licenses(context, filter: str = "all"):
    """
    Example data provider with optional parameter and default value.

    Args:
        context: ExecutionContext
        filter: Filter mode ('all', 'available', 'assigned')

    Returns:
        List of license options based on filter
    """
    all_licenses = [
        {"label": "Microsoft 365 E3", "value": "SPE_E3",
            "metadata": {"available": 10, "assigned": 5}},
        {"label": "Microsoft 365 E5", "value": "SPE_E5",
            "metadata": {"available": 0, "assigned": 3}},
        {"label": "Office 365 E1", "value": "O365_E1",
            "metadata": {"available": 20, "assigned": 0}},
    ]

    if filter == "available":
        return [lic for lic in all_licenses if lic["metadata"]["available"] > 0]
    elif filter == "assigned":
        return [lic for lic in all_licenses if lic["metadata"]["assigned"] > 0]
    else:
        return all_licenses
