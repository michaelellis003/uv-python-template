#!/usr/bin/env bash
# Initialize a new project from the python-package-template.
#
# This script renames the package directory, updates all references,
# resets the version and changelog, and regenerates the lockfile.
#
# Usage:
#   ./scripts/init.sh
#   ./scripts/init.sh --name my-cool-package
#   ./scripts/init.sh --name my-pkg --author "Jane Smith" --email jane@example.com \
#                     --github-owner janesmith --description "My awesome package"
#
# Prerequisites:
#   - uv installed (https://docs.astral.sh/uv/getting-started/installation/)
#   - Run from the project root directory

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

info()  { printf "${CYAN}==>${NC} %s\n" "$*"; }
ok()    { printf "${GREEN}==>${NC} %s\n" "$*"; }
warn()  { printf "${YELLOW}warning:${NC} %s\n" "$*"; }
error() { printf "${RED}error:${NC} %s\n" "$*" >&2; }

to_snake() { echo "$1" | tr '-' '_'; }
to_kebab() { echo "$1" | tr '_' '-'; }
to_title() { echo "$1" | tr '-' ' ' | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) substr($i,2)}1'; }

# Cross-platform in-place sed (BSD sed on macOS requires -i '')
sedi() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "$@"
    else
        sed -i "$@"
    fi
}

# Replace a sed pattern across all tracked project files
replace_all() {
    local pattern="$1"
    while IFS= read -r file; do
        sedi "$pattern" "$file" 2>/dev/null || true
    done <<< "$FILES_TO_UPDATE"
}

# Validate a package name: lowercase, starts with letter, only [a-z0-9-_]
validate_name() {
    local name="$1"
    if [[ ! "$name" =~ ^[a-z][a-z0-9_-]*$ ]]; then
        error "Invalid package name: '${name}'"
        echo "  Must start with a lowercase letter and contain only [a-z0-9_-]."
        return 1
    fi
    if [[ "$name" == "python-package-template" || "$name" == "python_package_template" ]]; then
        error "Please choose a name other than the template default."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Ensure we're in the project root
# ---------------------------------------------------------------------------

if [[ ! -f "pyproject.toml" ]]; then
    error "pyproject.toml not found. Run this script from the project root."
    exit 1
fi

if [[ ! -d "python_package_template" ]]; then
    error "python_package_template/ directory not found."
    error "Has this template already been initialized?"
    exit 1
fi

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

PROJECT_NAME=""
AUTHOR_NAME=""
AUTHOR_EMAIL=""
GITHUB_OWNER=""
DESCRIPTION=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --name|-n)
            PROJECT_NAME="$2"
            shift 2
            ;;
        --author)
            AUTHOR_NAME="$2"
            shift 2
            ;;
        --email)
            AUTHOR_EMAIL="$2"
            shift 2
            ;;
        --github-owner)
            GITHUB_OWNER="$2"
            shift 2
            ;;
        --description)
            DESCRIPTION="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: ./scripts/init.sh [OPTIONS]"
            echo ""
            echo "Interactive setup script for the python-package-template."
            echo "If options are not provided, you will be prompted for values."
            echo ""
            echo "Options:"
            echo "  --name, -n NAME       Package name (kebab-case)"
            echo "  --author NAME         Author name (e.g. 'Jane Smith')"
            echo "  --email EMAIL         Author email"
            echo "  --github-owner OWNER  GitHub username or organization"
            echo "  --description TEXT     Short project description"
            echo "  --help, -h            Show this help message"
            exit 0
            ;;
        *)
            error "Unknown argument: $1"
            echo "Run with --help for usage."
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Gather project info
# ---------------------------------------------------------------------------

echo ""
printf "${BOLD}Python Package Template — Project Setup${NC}\n"
echo "========================================="
echo ""
echo "This script will rename the package, update all references,"
echo "reset the version and changelog, and prepare your project."
echo ""

# Project name
if [[ -z "$PROJECT_NAME" ]]; then
    printf "${BOLD}Package name${NC} (kebab-case, e.g. my-cool-package): "
    read -r PROJECT_NAME
fi

KEBAB_NAME=$(to_kebab "$PROJECT_NAME")
SNAKE_NAME=$(to_snake "$PROJECT_NAME")
TITLE_NAME=$(to_title "$KEBAB_NAME")

validate_name "$KEBAB_NAME" || exit 1

# Author
if [[ -z "$AUTHOR_NAME" ]]; then
    printf "${BOLD}Author name${NC} (e.g. Jane Smith): "
    read -r AUTHOR_NAME
fi

if [[ -z "$AUTHOR_EMAIL" ]]; then
    printf "${BOLD}Author email${NC}: "
    read -r AUTHOR_EMAIL
fi

# GitHub
if [[ -z "$GITHUB_OWNER" ]]; then
    printf "${BOLD}GitHub owner${NC} (username or org): "
    read -r GITHUB_OWNER
fi

GITHUB_REPO="${GITHUB_OWNER}/${KEBAB_NAME}"

# Description
if [[ -z "$DESCRIPTION" ]]; then
    printf "${BOLD}Short description${NC} (one line): "
    read -r DESCRIPTION
fi

echo ""
echo "-----------------------------------------"
echo "  Package name (kebab):  ${KEBAB_NAME}"
echo "  Package name (snake):  ${SNAKE_NAME}"
echo "  Package name (title):  ${TITLE_NAME}"
echo "  Author:                ${AUTHOR_NAME} <${AUTHOR_EMAIL}>"
echo "  GitHub repo:           ${GITHUB_REPO}"
echo "  Description:           ${DESCRIPTION}"
echo "-----------------------------------------"
echo ""
printf "Proceed? [Y/n] "
read -r CONFIRM
if [[ "${CONFIRM,,}" == "n" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""

# ---------------------------------------------------------------------------
# 1. Rename the package directory
# ---------------------------------------------------------------------------

info "Renaming python_package_template/ -> ${SNAKE_NAME}/"
mv "python_package_template" "${SNAKE_NAME}"

# ---------------------------------------------------------------------------
# 2. Replace package name references in all files
# ---------------------------------------------------------------------------

info "Updating package name references..."

# Order matters: replace the longer/more specific patterns first
# so shorter patterns don't break longer matches.

# Files to update (excludes .git, caches, venv, lockfile, and this script)
FILES_TO_UPDATE=$(find . \
    -not -path './.git/*' \
    -not -path './.venv/*' \
    -not -path './.ruff_cache/*' \
    -not -path './.pytest_cache/*' \
    -not -path './*__pycache__*' \
    -not -path './uv.lock' \
    -not -path './CHANGELOG.md' \
    -not -name 'init.sh' \
    -type f \
    -print)

# --- GitHub URLs (most specific — must run before generic name replacement) ---
replace_all "s|michaelellis003/python-package-template|${GITHUB_REPO}|g"
replace_all "s|michaelellis003/uv-python-template|${GITHUB_REPO}|g"

# --- Author information ---
sedi "s/name = \"Michael Ellis\"/name = \"${AUTHOR_NAME}\"/" pyproject.toml
sedi "s|email = \"michaelellis003@gmail.com\"|email = \"${AUTHOR_EMAIL}\"|" pyproject.toml

# --- GitHub Pages site URL (must run before generic name replacement) ---
sedi "s|michaelellis003.github.io/uv-python-template|${GITHUB_OWNER}.github.io/${KEBAB_NAME}|g" mkdocs.yml

# --- Package name (generic replacements last) ---
# Replace python_package_template (snake_case — directory and import name)
replace_all "s/python_package_template/${SNAKE_NAME}/g"

# Replace python-package-template (kebab-case — pypi/metadata name)
replace_all "s/python-package-template/${KEBAB_NAME}/g"

# Replace Python Package Template (title case — README heading etc.)
replace_all "s/Python Package Template/${TITLE_NAME}/g"

# ---------------------------------------------------------------------------
# 3. Update project description
# ---------------------------------------------------------------------------

info "Updating project description..."

sedi "s|A production-ready template for starting new Python packages\.|${DESCRIPTION}|" pyproject.toml

# ---------------------------------------------------------------------------
# 4. Update README badges (remove codecov badge, update license badge)
# ---------------------------------------------------------------------------

info "Updating README badges..."

# Remove the codecov badge line (user will add their own when they set up codecov)
sedi '/codecov\.io/d' README.md

# The license badge URL was already updated by the GitHub URL replacement above

# Update the README description line
sedi "s|A production-ready template for starting new Python packages\. Clone it, rename a few things, and start building — dependency management, linting, type checking, testing, and CI/CD are already wired up\.|${DESCRIPTION}|" README.md

# ---------------------------------------------------------------------------
# 5. Update keywords
# ---------------------------------------------------------------------------

info "Updating keywords..."

sedi 's/keywords = \["template", "python", "uv", "ruff", "pyright"\]/keywords = []/' pyproject.toml

# ---------------------------------------------------------------------------
# 6. Reset version and changelog
# ---------------------------------------------------------------------------

info "Resetting version to 0.1.0..."

sedi 's/^version = ".*"/version = "0.1.0"/' pyproject.toml

info "Resetting CHANGELOG.md..."

cat > CHANGELOG.md << 'CHANGELOG_EOF'
# CHANGELOG

<!-- version list -->
CHANGELOG_EOF

# ---------------------------------------------------------------------------
# 7. Remove the TODO comment in pyproject.toml
# ---------------------------------------------------------------------------

info "Cleaning up TODO comments..."

sedi '/# TODO: Update the --upgrade-package/d' pyproject.toml

# ---------------------------------------------------------------------------
# 8. Update README structure and hints
# ---------------------------------------------------------------------------

info "Updating README..."

# Update project structure section — remove "(rename this)" hint
# (package name was already updated by the global replacement above)
sedi "s|# Package source (rename this)|# Package source|" README.md

# ---------------------------------------------------------------------------
# 9. Strip template-only content from README
# ---------------------------------------------------------------------------

info "Stripping template-only sections from README..."

# Replace the template-specific Getting Started + Customizing sections
# (enclosed in TEMPLATE-ONLY markers) with a project-appropriate version.
awk -v repo="${GITHUB_REPO}" -v name="${KEBAB_NAME}" '
/<!-- TEMPLATE-ONLY-START -->/ {
    skip = 1
    print "## Getting Started"
    print ""
    print "### Prerequisites"
    print "- Python 3.10+"
    print "- [uv](https://docs.astral.sh/uv/getting-started/installation/)"
    print ""
    print "### Installation"
    print ""
    print "```bash"
    printf "git clone https://github.com/%s.git\n", repo
    printf "cd %s\n", name
    print "uv sync"
    print "```"
    print ""
    print "### Running Tests"
    print ""
    print "```bash"
    print "uv run pytest -v --cov"
    print "```"
    print ""
    print "### Pre-commit Hooks"
    print ""
    print "```bash"
    print "uv run pre-commit install"
    print "```"
    next
}
/<!-- TEMPLATE-ONLY-END -->/ { skip = 0; next }
!skip { print }
' README.md > README.md.tmp && mv README.md.tmp README.md

# Remove "Customizing the Template" from Table of Contents
sedi '/Customizing the Template/d' README.md

# Remove init.sh from project structure diagrams
sedi '/init\.sh.*Interactive template/d' README.md
sedi '/init\.sh.*Interactive project/d' CLAUDE.md

# Strip template-only content from CLAUDE.md
awk -v name="${KEBAB_NAME}" -v desc="${DESCRIPTION}" '
/<!-- TEMPLATE-ONLY-START -->/ {
    skip = 1
    printf "**%s** — %s. Uses uv, Ruff, Pyright, and pre-commit\n", name, desc
    print "hooks. Licensed Apache-2.0."
    next
}
/<!-- TEMPLATE-ONLY-END -->/ { skip = 0; next }
!skip { print }
' CLAUDE.md > CLAUDE.md.tmp && mv CLAUDE.md.tmp CLAUDE.md

# ---------------------------------------------------------------------------
# 10. Regenerate the lockfile
# ---------------------------------------------------------------------------

info "Regenerating uv.lock..."

if command -v uv &>/dev/null; then
    uv lock 2>/dev/null
    ok "uv.lock regenerated."
else
    warn "uv not found. Run 'uv lock' manually after installing uv."
fi

# ---------------------------------------------------------------------------
# 11. Self-cleanup
# ---------------------------------------------------------------------------

info "Removing init script (no longer needed)..."
rm -f -- "$0"

# ---------------------------------------------------------------------------
# 12. Summary
# ---------------------------------------------------------------------------

echo ""
ok "Project initialized successfully!"
echo ""
echo "  Package directory:  ${SNAKE_NAME}/"
echo "  Package name:       ${KEBAB_NAME}"
echo "  Author:             ${AUTHOR_NAME} <${AUTHOR_EMAIL}>"
echo "  GitHub:             https://github.com/${GITHUB_REPO}"
echo ""
echo "Next steps:"
echo "  1. Review the changes:  git diff"
echo "  2. Install deps:        uv sync"
echo "  3. Run tests:           uv run pytest -v --cov"
echo "  4. Enable pre-commit:   uv run pre-commit install"
echo "  5. Replace the demo code in ${SNAKE_NAME}/main.py"
echo "  6. Set up Codecov and add the badge to README.md"
echo "  7. Enable GitHub Pages:  Settings > Pages > Source: GitHub Actions"
echo "  8. Push and run:        ./scripts/setup-repo.sh"
echo ""
