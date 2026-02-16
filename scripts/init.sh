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
#   ./scripts/init.sh --name my-pkg --pypi     # Enable PyPI publishing
#   ./scripts/init.sh --name my-pkg --license mit  # Select MIT license
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

# Fetch available licenses from the GitHub Licenses API.
# Falls back to a hardcoded list if the API is unavailable.
# Outputs lines of "key|name" pairs.
fetch_licenses() {
    local api_result
    api_result=$(curl -fsSL --max-time 5 \
        "https://api.github.com/licenses" 2>/dev/null) || true

    if [[ -n "$api_result" ]]; then
        python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
for lic in data:
    print(lic['key'] + '|' + lic['name'])
" <<< "$api_result" 2>/dev/null && return
    fi

    # Offline fallback
    info "GitHub API unavailable; using offline license list." >&2
    echo "apache-2.0|Apache License 2.0"
    echo "mit|MIT License"
    echo "bsd-3-clause|BSD 3-Clause \"New\" or \"Revised\" License"
    echo "gpl-3.0|GNU General Public License v3.0"
    echo "mpl-2.0|Mozilla Public License 2.0"
    echo "unlicense|The Unlicense"
}

# Fetch the full license text for a given SPDX key from the GitHub API.
# Replaces placeholder fields with the provided author and year.
# Args: $1=license_key $2=author_name $3=year
fetch_license_body() {
    local key="$1" author="$2" year="$3"
    local api_result
    api_result=$(curl -fsSL --max-time 5 \
        "https://api.github.com/licenses/${key}" 2>/dev/null) || true

    if [[ -z "$api_result" ]]; then
        warn "Could not fetch license text from GitHub API."
        warn "LICENSE file left unchanged."
        return 1
    fi

    python3 -c "
import json, sys
data = json.loads(sys.stdin.read())
body = data.get('body', '')
# Replace common placeholder variants
for placeholder in ['[year]', '[yyyy]', '<year>']:
    body = body.replace(placeholder, sys.argv[1])
for placeholder in ['[fullname]', '[name of copyright owner]',
                     '[name of copyright holder]', '<name of copyright owner>',
                     '<name of copyright holder>', '<copyright holders>']:
    body = body.replace(placeholder, sys.argv[2])
print(body, end='')
" "$year" "$author" <<< "$api_result"
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
ENABLE_PYPI=""
LICENSE_KEY=""
CURRENT_YEAR=$(date +%Y)

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
        --pypi)
            ENABLE_PYPI="y"
            shift
            ;;
        --license)
            LICENSE_KEY="$2"
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
            echo "  --pypi                Enable PyPI publishing (uncomments publish steps)"
            echo "  --license KEY         License SPDX key (e.g. mit, bsd-3-clause, gpl-3.0)"
            echo "                        Use 'none' to skip license setup"
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

# PyPI publishing
if [[ -z "$ENABLE_PYPI" ]]; then
    printf "${BOLD}Enable PyPI publishing?${NC} [y/N] "
    read -r ENABLE_PYPI
fi

echo ""
PYPI_ENABLED="no"
ENABLE_PYPI_LOWER=$(echo "$ENABLE_PYPI" | tr '[:upper:]' '[:lower:]')
if [[ "$ENABLE_PYPI_LOWER" == "y" || "$ENABLE_PYPI_LOWER" == "yes" ]]; then
    PYPI_ENABLED="yes"
fi

# License selection
LICENSE_SPDX=""
LICENSE_NAME=""
if [[ -z "$LICENSE_KEY" ]]; then
    echo ""
    info "Fetching available licenses..."
    LICENSE_LIST=$(fetch_licenses)

    echo ""
    printf "${BOLD}Select a license:${NC}\n"
    echo "  0) Skip (keep existing Apache-2.0, no license headers)"

    i=1
    while IFS='|' read -r key name; do
        printf "  %d) %s (%s)\n" "$i" "$name" "$key"
        eval "LICENSE_OPTION_${i}_KEY=\"${key}\""
        eval "LICENSE_OPTION_${i}_NAME=\"${name}\""
        i=$((i + 1))
    done <<< "$LICENSE_LIST"

    printf "\nChoice [0]: "
    read -r LICENSE_CHOICE
    LICENSE_CHOICE="${LICENSE_CHOICE:-0}"

    if [[ "$LICENSE_CHOICE" == "0" ]]; then
        LICENSE_KEY="none"
    elif [[ "$LICENSE_CHOICE" -ge 1 && "$LICENSE_CHOICE" -lt "$i" ]] 2>/dev/null; then
        eval "LICENSE_KEY=\${LICENSE_OPTION_${LICENSE_CHOICE}_KEY}"
        eval "LICENSE_NAME=\${LICENSE_OPTION_${LICENSE_CHOICE}_NAME}"
    else
        error "Invalid choice: ${LICENSE_CHOICE}"
        exit 1
    fi
elif [[ "$(echo "$LICENSE_KEY" | tr '[:upper:]' '[:lower:]')" != "none" ]]; then
    # Non-interactive: validate the key against the API
    LICENSE_LIST=$(fetch_licenses)
    LICENSE_NAME=$(echo "$LICENSE_LIST" | grep -i "^${LICENSE_KEY}|" | head -1 | cut -d'|' -f2)
    if [[ -z "$LICENSE_NAME" ]]; then
        error "Unknown license key: '${LICENSE_KEY}'"
        echo "  Available keys:"
        echo "$LICENSE_LIST" | while IFS='|' read -r key name; do
            echo "    ${key} — ${name}"
        done
        exit 1
    fi
    # Normalize the key to match API casing
    LICENSE_KEY=$(echo "$LICENSE_LIST" | grep -i "^${LICENSE_KEY}|" | head -1 | cut -d'|' -f1)
fi

LICENSE_KEY_LOWER=$(echo "$LICENSE_KEY" | tr '[:upper:]' '[:lower:]')
if [[ "$LICENSE_KEY_LOWER" == "none" ]]; then
    LICENSE_SPDX="Apache-2.0"
    LICENSE_NAME="Apache License 2.0 (unchanged)"
else
    # Map common license keys to SPDX identifiers
    LICENSE_SPDX=$(python3 -c "
spdx_map = {
    'agpl-3.0': 'AGPL-3.0-only',
    'apache-2.0': 'Apache-2.0',
    'bsd-2-clause': 'BSD-2-Clause',
    'bsd-3-clause': 'BSD-3-Clause',
    'bsl-1.0': 'BSL-1.0',
    'cc0-1.0': 'CC0-1.0',
    'epl-2.0': 'EPL-2.0',
    'gpl-2.0': 'GPL-2.0-only',
    'gpl-3.0': 'GPL-3.0-only',
    'lgpl-2.1': 'LGPL-2.1-only',
    'mit': 'MIT',
    'mpl-2.0': 'MPL-2.0',
    'unlicense': 'Unlicense',
}
print(spdx_map.get('${LICENSE_KEY}', '${LICENSE_KEY}'.upper()))
")
fi

echo "-----------------------------------------"
echo "  Package name (kebab):  ${KEBAB_NAME}"
echo "  Package name (snake):  ${SNAKE_NAME}"
echo "  Package name (title):  ${TITLE_NAME}"
echo "  Author:                ${AUTHOR_NAME} <${AUTHOR_EMAIL}>"
echo "  GitHub repo:           ${GITHUB_REPO}"
echo "  Description:           ${DESCRIPTION}"
echo "  PyPI publishing:       ${PYPI_ENABLED}"
echo "  License:               ${LICENSE_NAME} (${LICENSE_SPDX})"
echo "-----------------------------------------"
echo ""
printf "Proceed? [Y/n] "
read -r CONFIRM
CONFIRM_LOWER=$(echo "$CONFIRM" | tr '[:upper:]' '[:lower:]')
if [[ "$CONFIRM_LOWER" == "n" ]]; then
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
    -not -path './tests/template/*' \
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
replace_all "s|michaelellis003.github.io/uv-python-template|${GITHUB_OWNER}.github.io/${KEBAB_NAME}|g"

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

# Update conda-forge recipe metadata
if [[ -f recipe/meta.yaml ]]; then
    sedi "s|A production-ready template for starting new Python packages\.|${DESCRIPTION}|" recipe/meta.yaml
    sedi "s|michaelellis003|${GITHUB_OWNER}|g" recipe/meta.yaml
fi

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
# 9. Generate license files and apply headers
# ---------------------------------------------------------------------------

if [[ "$LICENSE_KEY_LOWER" != "none" ]]; then
    info "Setting up license (${LICENSE_SPDX})..."

    # Fetch and write the LICENSE file
    LICENSE_BODY=$(fetch_license_body "$LICENSE_KEY" "$AUTHOR_NAME" "$CURRENT_YEAR")
    if [[ -n "$LICENSE_BODY" ]]; then
        echo "$LICENSE_BODY" > LICENSE
        ok "LICENSE file updated."
    fi

    # Update pyproject.toml license field
    sedi "s|license = {text = \"Apache-2.0\"}|license = {text = \"${LICENSE_SPDX}\"}|" pyproject.toml

    # Generate LICENSE_HEADER for the insert-license pre-commit hook
    cat > LICENSE_HEADER << HEADER_EOF
Copyright ${CURRENT_YEAR} ${AUTHOR_NAME}
SPDX-License-Identifier: ${LICENSE_SPDX}
HEADER_EOF
    ok "LICENSE_HEADER generated."

    # Add the insert-license pre-commit hook (before the ruff block)
    python3 -c "
import sys

content = open('.pre-commit-config.yaml').read()
hook_block = '''  - repo: https://github.com/Lucas-C/pre-commit-hooks
    rev: v1.5.5
    hooks:
      - id: insert-license
        files: \\\\.py$
        args:
          - --license-filepath=LICENSE_HEADER
          - --comment-style=#
          - --detect-license-in-X-top-lines=5
'''
# Insert before the ruff-pre-commit block
marker = '  # Keep rev in sync with ruff version'
content = content.replace(marker, hook_block + marker)
open('.pre-commit-config.yaml', 'w').write(content)
"
    ok "insert-license pre-commit hook added."

    # Apply SPDX headers to all .py files
    info "Applying license headers to .py files..."
    HEADER_LINE1="# Copyright ${CURRENT_YEAR} ${AUTHOR_NAME}"
    HEADER_LINE2="# SPDX-License-Identifier: ${LICENSE_SPDX}"

    find "${SNAKE_NAME}" tests -name '*.py' -type f | while IFS= read -r pyfile; do
        # Handle shebang lines
        first_line=$(head -1 "$pyfile")
        if [[ "$first_line" == "#!"* ]]; then
            rest=$(tail -n +2 "$pyfile")
            {
                echo "$first_line"
                echo "$HEADER_LINE1"
                echo "$HEADER_LINE2"
                echo "$rest"
            } > "${pyfile}.tmp" && mv "${pyfile}.tmp" "$pyfile"
        else
            {
                echo "$HEADER_LINE1"
                echo "$HEADER_LINE2"
                cat "$pyfile"
            } > "${pyfile}.tmp" && mv "${pyfile}.tmp" "$pyfile"
        fi
    done
    ok "License headers applied."
else
    info "Skipping license setup (keeping Apache-2.0 defaults)."
fi

# ---------------------------------------------------------------------------
# 10. Strip template-only content
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
awk -v name="${KEBAB_NAME}" -v desc="${DESCRIPTION}" -v lic="${LICENSE_SPDX}" '
/<!-- TEMPLATE-ONLY-START -->/ {
    skip = 1
    printf "**%s** — %s. Uses uv, Ruff, Pyright, and pre-commit\n", name, desc
    printf "hooks. Licensed %s.\n", lic
    next
}
/<!-- TEMPLATE-ONLY-END -->/ { skip = 0; next }
!skip { print }
' CLAUDE.md > CLAUDE.md.tmp && mv CLAUDE.md.tmp CLAUDE.md

# ---------------------------------------------------------------------------
# 11. Enable PyPI publishing (if requested)
# ---------------------------------------------------------------------------

if [[ "$PYPI_ENABLED" == "yes" ]]; then
    info "Enabling PyPI publishing steps in workflows..."

    # Uncomment the publish steps between PYPI-START and PYPI-END markers
    for workflow in .github/workflows/release.yml; do
        awk '
        /# PYPI-START/ { in_block = 1; next }
        /# PYPI-END/   { in_block = 0; next }
        in_block && /^      # / { sub(/^      # /, "      "); print; next }
        { print }
        ' "$workflow" > "${workflow}.tmp" && mv "${workflow}.tmp" "$workflow"
    done

    ok "PyPI publishing enabled in release.yml."
fi

# ---------------------------------------------------------------------------
# 12. Regenerate the lockfile
# ---------------------------------------------------------------------------

info "Regenerating uv.lock..."

if command -v uv &>/dev/null; then
    uv lock 2>/dev/null
    ok "uv.lock regenerated."
else
    warn "uv not found. Run 'uv lock' manually after installing uv."
fi

# ---------------------------------------------------------------------------
# 13. Post-init validation
# ---------------------------------------------------------------------------

info "Validating initialized project..."
VALIDATION_OK=true

# Verify the renamed package can be imported
if command -v uv &>/dev/null; then
    if ! uv run python -c "import ${SNAKE_NAME}" 2>/dev/null; then
        warn "Could not import '${SNAKE_NAME}'. Check the renamed package."
        VALIDATION_OK=false
    fi
fi

# Check for stale template references in tracked files
STALE_REFS=$(grep -rl 'python_package_template\|python-package-template' \
    --include='*.py' --include='*.toml' --include='*.yml' --include='*.yaml' \
    --include='*.md' --include='*.cfg' \
    . 2>/dev/null \
    | grep -v '.git/' \
    | grep -v 'uv.lock' \
    | grep -v 'init.sh' \
    | grep -v 'tests/template/' \
    || true)

if [[ -n "$STALE_REFS" ]]; then
    warn "Stale template references found in:"
    echo "$STALE_REFS" | while IFS= read -r f; do echo "    $f"; done
    VALIDATION_OK=false
fi

if [[ "$VALIDATION_OK" == "true" ]]; then
    ok "Validation passed."
fi

# ---------------------------------------------------------------------------
# 14. Self-cleanup
# ---------------------------------------------------------------------------

info "Removing init script (no longer needed)..."
rm -f -- "$0"

# Remove template-specific tests (not needed for derived projects)
if [[ -d "tests/template" ]]; then
    rm -rf tests/template

    # Remove tests/template/ references from documentation
    sedi '/template\/.*# Template-specific/d' CLAUDE.md
    sedi '/conftest.py.*# Fixtures: template_dir/d' CLAUDE.md
    sedi '/test_template_structure/d' CLAUDE.md
    sedi '/test_init_license/d' CLAUDE.md
    sedi '/template\/.*# Template tests/d' README.md
    sedi '/test_template_structure.*Verifies template/d' README.md
    sedi '/test_init_license.*Integration tests/d' README.md

    ok "Template tests removed."
fi

# ---------------------------------------------------------------------------
# 15. Summary
# ---------------------------------------------------------------------------

echo ""
ok "Project initialized successfully!"
echo ""
echo "  Package directory:  ${SNAKE_NAME}/"
echo "  Package name:       ${KEBAB_NAME}"
echo "  Author:             ${AUTHOR_NAME} <${AUTHOR_EMAIL}>"
echo "  GitHub:             https://github.com/${GITHUB_REPO}"
echo "  PyPI publishing:    ${PYPI_ENABLED}"
echo "  License:            ${LICENSE_SPDX}"
echo ""
echo "Next steps:"
echo "  1. Review the changes:     git diff"
echo "  2. Install deps:           uv sync"
echo "  3. Run tests:              uv run pytest -v --cov"
echo "  4. Enable pre-commit:      uv run pre-commit install"
echo "  5. Replace the demo code in ${SNAKE_NAME}/main.py"
echo "  6. Commit initialized state:"
echo "       git add -A && git commit -m 'chore: initialize from template'"
echo "  7. Push to your repo:"
echo "       git remote set-url origin <your-repo-url>"
echo "       git push -u origin main"
echo "  8. Set up Codecov and add the badge to README.md"
echo "  9. Enable GitHub Pages:    Settings > Pages > Source: GitHub Actions"
echo "  10. Set up branch protection: ./scripts/setup-repo.sh"

if [[ "$PYPI_ENABLED" == "yes" ]]; then
    echo ""
    printf "${BOLD}PyPI setup:${NC}\n"
    echo "  1. Go to https://pypi.org/manage/account/publishing/"
    echo "  2. Add a trusted publisher:"
    echo "       Owner:    ${GITHUB_OWNER}"
    echo "       Repo:     ${KEBAB_NAME}"
    echo "       Workflow: release.yml"
    echo "  3. (Optional) Set up TestPyPI the same way at"
    echo "     https://test.pypi.org/manage/account/publishing/"
    echo "     with workflow: test-publish.yml"
fi

echo ""
