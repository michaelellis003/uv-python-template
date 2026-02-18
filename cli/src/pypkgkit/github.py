"""Git and GitHub operations for pypkgkit."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_RULESET_NAME = 'main branch protection'


def check_git_installed() -> bool:
    """Check whether git is available on PATH.

    Returns:
        True if git is found and runs successfully.
    """
    try:
        result = subprocess.run(
            ['git', '--version'],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_gh_installed() -> bool:
    """Check whether gh CLI is available on PATH.

    Returns:
        True if gh is found and runs successfully.
    """
    try:
        result = subprocess.run(
            ['gh', '--version'],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_gh_authenticated() -> bool:
    """Check whether gh is authenticated.

    Returns:
        True if gh auth status succeeds.
    """
    result = subprocess.run(
        ['gh', 'auth', 'status'],
        capture_output=True,
    )
    return result.returncode == 0


def detect_gh_owner() -> str | None:
    """Auto-detect GitHub username from gh auth.

    Returns:
        GitHub username string, or None on failure.
    """
    result = subprocess.run(
        ['gh', 'api', 'user', '--jq', '.login'],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    owner = result.stdout.strip()
    return owner or None


def git_init(project_dir: Path) -> int:
    """Initialize git repo and create initial commit.

    Args:
        project_dir: Path to the project directory.

    Returns:
        First non-zero returncode, or 0 on success.
    """
    commands = [
        ['git', 'init'],
        ['git', 'add', '.'],
        ['git', 'commit', '-m', 'Initial commit from pypkgkit'],
    ]
    for cmd in commands:
        result = subprocess.run(cmd, cwd=project_dir, capture_output=True)
        if result.returncode != 0:
            return result.returncode
    return 0


def git_push(project_dir: Path) -> int:
    """Push to origin main.

    Args:
        project_dir: Path to the project directory.

    Returns:
        Process return code.
    """
    result = subprocess.run(
        ['git', 'push', '-u', 'origin', 'main'],
        cwd=project_dir,
        capture_output=True,
    )
    return result.returncode


def create_github_repo(
    project_dir: Path,
    *,
    owner: str,
    name: str,
    description: str = '',
    private: bool = False,
) -> int:
    """Create GitHub repo and add as origin remote.

    Args:
        project_dir: Path to the project directory.
        owner: GitHub username or organization.
        name: Repository name.
        description: Short repository description.
        private: Create a private repository.

    Returns:
        First non-zero returncode, or 0 on success.
    """
    cmd = [
        'gh',
        'repo',
        'create',
        f'{owner}/{name}',
        '--private' if private else '--public',
    ]
    if description:
        cmd.extend(['--description', description])

    result = subprocess.run(cmd, cwd=project_dir, capture_output=True)
    if result.returncode != 0:
        return result.returncode

    remote_url = f'https://github.com/{owner}/{name}.git'
    result = subprocess.run(
        ['git', 'remote', 'add', 'origin', remote_url],
        cwd=project_dir,
        capture_output=True,
    )
    return result.returncode


def _build_ruleset_payload(*, require_reviews: int = 0) -> dict:
    """Build ruleset JSON payload matching setup-repo.sh.

    Args:
        require_reviews: Number of required PR approvals.

    Returns:
        Ruleset payload dict.
    """
    return {
        'name': _RULESET_NAME,
        'target': 'branch',
        'enforcement': 'active',
        'conditions': {
            'ref_name': {
                'include': ['refs/heads/main'],
                'exclude': [],
            }
        },
        'bypass_actors': [
            {
                'actor_id': 5,
                'actor_type': 'RepositoryRole',
                'bypass_mode': 'always',
            }
        ],
        'rules': [
            {
                'type': 'pull_request',
                'parameters': {
                    'required_approving_review_count': (require_reviews),
                    'dismiss_stale_reviews_on_push': False,
                    'require_code_owner_review': False,
                    'require_last_push_approval': False,
                    'required_review_thread_resolution': False,
                },
            },
            {
                'type': 'required_status_checks',
                'parameters': {
                    'strict_required_status_checks_policy': True,
                    'required_status_checks': [{'context': 'ci-pass'}],
                },
            },
            {'type': 'non_fast_forward'},
            {'type': 'deletion'},
        ],
    }


def setup_ruleset(*, owner: str, name: str, require_reviews: int = 0) -> int:
    """Create or update branch protection ruleset (idempotent).

    Args:
        owner: GitHub username or organization.
        name: Repository name.
        require_reviews: Number of required PR approvals.

    Returns:
        0 on success, non-zero on failure.
    """
    # Check for existing ruleset
    result = subprocess.run(
        [
            'gh',
            'api',
            f'repos/{owner}/{name}/rulesets',
            '--jq',
            f'.[] | select(.name == "{_RULESET_NAME}") | .id',
        ],
        capture_output=True,
        text=True,
    )
    existing_id = result.stdout.strip() if result.returncode == 0 else ''

    payload = _build_ruleset_payload(require_reviews=require_reviews)
    payload_json = json.dumps(payload)

    if existing_id:
        endpoint = f'repos/{owner}/{name}/rulesets/{existing_id}'
        method = 'PUT'
    else:
        endpoint = f'repos/{owner}/{name}/rulesets'
        method = 'POST'

    result = subprocess.run(
        [
            'gh',
            'api',
            endpoint,
            '--method',
            method,
            '--input',
            '-',
        ],
        input=payload_json,
        capture_output=True,
        text=True,
    )
    return result.returncode


def _err(msg: str) -> int:
    """Print an error message and return 1.

    Args:
        msg: Error message.

    Returns:
        Always returns 1.
    """
    print(f'error: {msg}', file=sys.stderr)
    return 1


def setup_github(
    project_dir: Path,
    *,
    owner: str,
    repo_name: str,
    description: str = '',
    private: bool = False,
    require_reviews: int = 0,
) -> int:
    """Full GitHub pipeline: create repo, push, configure rulesets.

    Args:
        project_dir: Path to the project directory.
        owner: GitHub username or organization.
        repo_name: Repository name.
        description: Short repository description.
        private: Create a private repository.
        require_reviews: Number of required PR approvals.

    Returns:
        0 on success, non-zero on failure.
    """
    if not check_gh_installed():
        return _err(
            'gh CLI is not installed. Install from https://cli.github.com'
        )

    if not check_gh_authenticated():
        return _err('gh is not authenticated. Run: gh auth login')

    print('Creating GitHub repository...')
    rc = create_github_repo(
        project_dir,
        owner=owner,
        name=repo_name,
        description=description,
        private=private,
    )
    if rc != 0:
        return _err('Failed to create GitHub repository')

    print('Pushing to GitHub...')
    rc = git_push(project_dir)
    if rc != 0:
        return _err('Failed to push to GitHub')

    print('Configuring branch protection rulesets...')
    rc = setup_ruleset(
        owner=owner,
        name=repo_name,
        require_reviews=require_reviews,
    )
    if rc != 0:
        return _err('Failed to configure rulesets')

    visibility = 'private' if private else 'public'
    print(f'Done! Repository {owner}/{repo_name} ({visibility}) is ready.')
    return 0
