#!/usr/bin/env bash
# Setup script for repos created from python-package-template.
#
# Configures branch protection on main with required CI status checks.
# GitHub does not copy branch protection rules from template repos, so
# this must be run once after creating a new repo.
#
# Prerequisites:
#   - gh CLI installed and authenticated (https://cli.github.com)
#   - Admin access to the target repository
#
# Usage:
#   ./scripts/setup-repo.sh

set -euo pipefail

# Detect repo from git remote
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || {
    echo "Error: could not detect repository." >&2
    echo "Run this from inside a GitHub-connected git repo." >&2
    exit 1
}

echo "Configuring branch protection for ${REPO} (main)..."

gh api "repos/${REPO}/branches/main/protection" \
    --method PUT \
    --input - <<'JSON'
{
  "required_status_checks": {
    "strict": true,
    "checks": [
      { "context": "ruff-lint" },
      { "context": "ruff-format" },
      { "context": "pyright" },
      { "context": "pytest (3.10)" },
      { "context": "pytest (3.11)" },
      { "context": "pytest (3.12)" },
      { "context": "pytest (3.13)" }
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": null,
  "restrictions": null
}
JSON

echo "Done. Branch protection enabled on main."
echo ""
echo "Required status checks:"
echo "  - ruff-lint"
echo "  - ruff-format"
echo "  - pyright"
echo "  - pytest (3.10, 3.11, 3.12, 3.13)"
echo ""
echo "Note: if you change the Python version matrix in ci.yml,"
echo "update the pytest checks above to match."
