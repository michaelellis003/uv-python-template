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
#   ./scripts/setup-repo.sh --require-reviews 1

set -euo pipefail

# --- Configuration ---------------------------------------------------------
# Number of required PR approvals before merging.
# Set to 0 to skip PR review requirements (default, suitable for solo devs).
# Use --require-reviews N to override.
REQUIRED_REVIEWS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --require-reviews)
            REQUIRED_REVIEWS="${2:-1}"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./scripts/setup-repo.sh [--require-reviews N]"
            echo ""
            echo "Options:"
            echo "  --require-reviews N  Require N PR approvals (default: 0)"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Run with --help for usage." >&2
            exit 1
            ;;
    esac
done

# Detect repo from git remote
REPO=$(gh repo view --json nameWithOwner --jq '.nameWithOwner' 2>/dev/null) || {
    echo "Error: could not detect repository." >&2
    echo "Run this from inside a GitHub-connected git repo." >&2
    exit 1
}

echo "Configuring branch protection for ${REPO} (main)..."

# Build the PR reviews JSON value
if [[ "$REQUIRED_REVIEWS" -gt 0 ]]; then
    REVIEWS_VALUE="{ \"required_approving_review_count\": $REQUIRED_REVIEWS }"
else
    REVIEWS_VALUE="null"
fi

gh api "repos/${REPO}/branches/main/protection" \
    --method PUT \
    --input - <<EOF
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
  "required_pull_request_reviews": ${REVIEWS_VALUE},
  "restrictions": null
}
EOF

echo "Done. Branch protection enabled on main."
echo ""
echo "Required status checks:"
echo "  - ruff-lint"
echo "  - ruff-format"
echo "  - pyright"
echo "  - pytest (3.10, 3.11, 3.12, 3.13)"
if [[ "$REQUIRED_REVIEWS" -gt 0 ]]; then
    echo ""
    echo "Required PR approvals: $REQUIRED_REVIEWS"
else
    echo ""
    echo "PR reviews: not required (solo developer mode)"
    echo "  To require reviews: ./scripts/setup-repo.sh --require-reviews 1"
fi
echo ""
echo "Note: if you change the Python version matrix in ci.yml,"
echo "update the pytest checks above to match."
