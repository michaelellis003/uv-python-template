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

# Ensure sed can handle UTF-8 content on macOS (prevents "illegal byte
# sequence" errors when processing files with non-ASCII characters).
if [[ "$OSTYPE" == "darwin"* ]]; then
    export LC_ALL=en_US.UTF-8
fi

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
trim()     { printf '%s' "$1" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'; }

# Prompt for a required input with retry loop.
# Errors and exits if stdin is not a terminal (non-interactive).
# Usage: prompt_required VARIABLE_NAME "Prompt text" "--flag-name"
prompt_required() {
    local var_name="$1" prompt="$2" flag="$3"
    local value="${!var_name}"
    value=$(trim "$value")
    while [[ -z "$value" ]]; do
        if [[ ! -t 0 ]]; then
            error "${prompt} is required (use ${flag} in non-interactive mode)"
            exit 1
        fi
        printf "${BOLD}%s${NC}: " "$prompt"
        read -r value
        value=$(trim "$value")
        if [[ -z "$value" ]]; then
            warn "${prompt} cannot be empty."
        fi
    done
    eval "${var_name}=\"\${value}\""
}

require_arg() {
    local flag="$1"
    local nargs="$2"
    if [[ "$nargs" -lt 2 ]]; then
        error "Option ${flag} requires a value"
        echo "  Run with --help for usage."
        exit 1
    fi
}

escape_sed_replacement() {
    printf '%s' "$1" | sed -e 's/[\\|&]/\\&/g'
}

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
    local failed=false
    while IFS= read -r file; do
        if ! sedi "$pattern" "$file"; then
            warn "sed failed on: $file"
            failed=true
        fi
    done <<< "$FILES_TO_UPDATE"
    if [[ "$failed" == "true" ]]; then
        return 1
    fi
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
    # Reject names that shadow common Python stdlib modules
    local snake
    snake=$(to_snake "$name")
    local stdlib_names
    stdlib_names=" abc ast asyncio base64 collections contextlib copy csv "
    stdlib_names+="dataclasses datetime decimal enum functools hashlib http "
    stdlib_names+="importlib inspect io itertools json logging math "
    stdlib_names+="multiprocessing operator os pathlib pickle platform "
    stdlib_names+="pprint queue random re secrets shutil signal socket "
    stdlib_names+="sqlite3 string struct subprocess sys test textwrap "
    stdlib_names+="threading time tomllib typing unittest uuid warnings "
    stdlib_names+="xml zipfile "
    if [[ "$stdlib_names" == *" ${snake} "* ]]; then
        error "Package name '${name}' would shadow the Python stdlib module '${snake}'."
        echo "  Choose a different name to avoid import conflicts."
        return 1
    fi
}

# Validate a GitHub username or organization name
validate_author_name() {
    local name="$1"
    if [[ "$name" == *$'\n'* || "$name" == *$'\r'* ]]; then
        error "Author name must be a single line."
        return 1
    fi
}

validate_email() {
    local email="$1"
    if [[ ! "$email" == *@* ]]; then
        error "Invalid email: '${email}' (must contain @)"
        return 1
    fi
    if [[ "$email" == *$'\n'* || "$email" == *$'\r'* ]]; then
        error "Email must be a single line."
        return 1
    fi
}

validate_github_owner() {
    local owner="$1"
    if [[ ! "$owner" =~ ^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$ ]]; then
        error "Invalid GitHub owner: '${owner}'"
        echo "  Must contain only alphanumeric characters or hyphens,"
        echo "  and cannot begin or end with a hyphen."
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

if ! command -v python3 &>/dev/null; then
    error "python3 is required but not found. Please install Python 3."
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
            require_arg "$1" "$#"
            PROJECT_NAME="$2"
            shift 2
            ;;
        --author)
            require_arg "$1" "$#"
            AUTHOR_NAME="$2"
            shift 2
            ;;
        --email)
            require_arg "$1" "$#"
            AUTHOR_EMAIL="$2"
            shift 2
            ;;
        --github-owner)
            require_arg "$1" "$#"
            GITHUB_OWNER="$2"
            shift 2
            ;;
        --description)
            require_arg "$1" "$#"
            DESCRIPTION="$2"
            shift 2
            ;;
        --pypi)
            ENABLE_PYPI="y"
            shift
            ;;
        --license)
            require_arg "$1" "$#"
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
prompt_required PROJECT_NAME "Package name (kebab-case, e.g. my-cool-package)" "--name"

KEBAB_NAME=$(to_kebab "$PROJECT_NAME")
SNAKE_NAME=$(to_snake "$PROJECT_NAME")
TITLE_NAME=$(to_title "$KEBAB_NAME")

validate_name "$KEBAB_NAME" || exit 1

# Author
prompt_required AUTHOR_NAME "Author name (e.g. Jane Smith)" "--author"
validate_author_name "$AUTHOR_NAME" || exit 1
prompt_required AUTHOR_EMAIL "Author email" "--email"
validate_email "$AUTHOR_EMAIL" || exit 1

# GitHub
prompt_required GITHUB_OWNER "GitHub owner (username or org)" "--github-owner"
validate_github_owner "$GITHUB_OWNER" || exit 1

GITHUB_REPO="${GITHUB_OWNER}/${KEBAB_NAME}"

# Description
if [[ -z "$DESCRIPTION" ]]; then
    printf "${BOLD}Short description${NC} (one line): "
    read -r DESCRIPTION
fi
DESCRIPTION=$(trim "$DESCRIPTION")
if [[ "$DESCRIPTION" == *$'\n'* || "$DESCRIPTION" == *$'\r'* ]]; then
    error "Description must be a single line."
    exit 1
fi

# Escape description for use in sed replacements
DESCRIPTION_SED=$(escape_sed_replacement "$DESCRIPTION")

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

# Files to update (excludes .git, caches, venv, lockfile, build artifacts,
# binary files, and this script)
FILES_TO_UPDATE=$(find . \
    -not -path './.git/*' \
    -not -path './.venv/*' \
    -not -path './.ruff_cache/*' \
    -not -path './.pytest_cache/*' \
    -not -path './*__pycache__*' \
    -not -path './tests/template/*' \
    -not -path './site/*' \
    -not -path './dist/*' \
    -not -path './build/*' \
    -not -path './uv.lock' \
    -not -path './CHANGELOG.md' \
    -not -name 'init.sh' \
    -not -name '.coverage' \
    -not -name '*.png' \
    -not -name '*.jpg' \
    -not -name '*.gif' \
    -not -name '*.ico' \
    -not -name '*.gz' \
    -not -name '*.zip' \
    -not -name '*.whl' \
    -not -name '*.tar' \
    -not -name '*.inv' \
    -not -name '*.so' \
    -not -name '*.dylib' \
    -type f \
    -print)

# --- GitHub URLs (most specific — must run before generic name replacement) ---
replace_all "s|michaelellis003/python-package-template|${GITHUB_REPO}|g"
replace_all "s|michaelellis003/uv-python-template|${GITHUB_REPO}|g"

# --- Author information ---
AUTHOR_NAME_SED=$(escape_sed_replacement "$AUTHOR_NAME")
AUTHOR_EMAIL_SED=$(escape_sed_replacement "$AUTHOR_EMAIL")
sedi "s/name = \"Michael Ellis\"/name = \"${AUTHOR_NAME_SED}\"/" pyproject.toml
sedi "s|email = \"michaelellis003@gmail.com\"|email = \"${AUTHOR_EMAIL_SED}\"|" pyproject.toml

# --- CODEOWNERS ---
sedi "s|@michaelellis003|@${GITHUB_OWNER}|g" .github/CODEOWNERS

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

sedi "s|A production-ready template for starting new Python packages\.|${DESCRIPTION_SED}|" pyproject.toml

# Update conda-forge recipe metadata
if [[ -f recipe/meta.yaml ]]; then
    sedi "s|A production-ready template for starting new Python packages\.|${DESCRIPTION_SED}|" recipe/meta.yaml
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
sedi "s|A production-ready template for starting new Python packages\. Clone it, rename a few things, and start building — dependency management, linting, type checking, testing, and CI/CD are already wired up\.|${DESCRIPTION_SED}|" README.md

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

VALIDATION_OK=true

if [[ "$LICENSE_KEY_LOWER" != "none" ]]; then
    info "Setting up license (${LICENSE_SPDX})..."

    # Fetch and write the LICENSE file (|| true: API failure is handled below)
    LICENSE_BODY=$(fetch_license_body "$LICENSE_KEY" "$AUTHOR_NAME" "$CURRENT_YEAR") || true
    if [[ -n "$LICENSE_BODY" ]]; then
        printf '%s\n' "$LICENSE_BODY" > LICENSE
        ok "LICENSE file updated."
    else
        warn "Could not fetch license text. LICENSE file still contains Apache-2.0."
        warn "Replace the LICENSE file manually with your ${LICENSE_SPDX} license text."
        VALIDATION_OK=false
    fi

    # Update pyproject.toml license field (always — user explicitly chose this license)
    sedi "s|license = {text = \"Apache-2.0\"}|license = {text = \"${LICENSE_SPDX}\"}|" pyproject.toml

    # Update license trove classifier (PEP 639 license field is authoritative,
    # but keep the classifier in sync for tools that read it)
    LICENSE_CLASSIFIER=$(python3 -c "
classifier_map = {
    'MIT': 'License :: OSI Approved :: MIT License',
    'Apache-2.0': 'License :: OSI Approved :: Apache Software License',
    'BSD-2-Clause': 'License :: OSI Approved :: BSD License',
    'BSD-3-Clause': 'License :: OSI Approved :: BSD License',
    'GPL-2.0-only': 'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
    'GPL-3.0-only': 'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
    'LGPL-2.1-only': 'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
    'AGPL-3.0-only': 'License :: OSI Approved :: GNU Affero General Public License v3',
    'MPL-2.0': 'License :: OSI Approved :: Mozilla Public License 2.0 (MPL 2.0)',
    'Unlicense': 'License :: OSI Approved :: The Unlicense (Unlicense)',
    'BSL-1.0': 'License :: OSI Approved :: Boost Software License 1.0 (BSL-1.0)',
    'CC0-1.0': 'License :: CC0 1.0 Universal (CC0 1.0) Public Domain Dedication',
    'EPL-2.0': 'License :: OSI Approved :: Eclipse Public License 2.0 (EPL-2.0)',
}
print(classifier_map.get('${LICENSE_SPDX}', ''))
")
    if [[ -n "$LICENSE_CLASSIFIER" ]]; then
        sedi "s|License :: OSI Approved :: Apache Software License|${LICENSE_CLASSIFIER}|" pyproject.toml
    else
        # No known classifier — remove the stale Apache one
        sedi "/License :: OSI Approved :: Apache Software License/d" pyproject.toml
        warn "No trove classifier mapping for ${LICENSE_SPDX}. Removed stale Apache classifier."
    fi

    # Update conda-forge recipe license field
    if [[ -f recipe/meta.yaml ]]; then
        sedi "s|license: Apache-2.0|license: ${LICENSE_SPDX}|" recipe/meta.yaml
    fi

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
if marker not in content:
    print('Marker not found in .pre-commit-config.yaml', file=sys.stderr)
    sys.exit(1)
content = content.replace(marker, hook_block + marker)
open('.pre-commit-config.yaml', 'w').write(content)
" && ok "insert-license pre-commit hook added." || {
        warn "Could not add insert-license hook to .pre-commit-config.yaml."
        warn "Add it manually. See https://github.com/Lucas-C/pre-commit-hooks"
        VALIDATION_OK=false
    }

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

# Rewrite docs/index.md (remove template description and init.sh instructions)
cat > docs/index.md << DOCS_INDEX_EOF
# ${TITLE_NAME}

${DESCRIPTION}

## Features

- **[uv](https://docs.astral.sh/uv/)** for fast Python package management
- **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting
- **[Pyright](https://github.com/microsoft/pyright)** for static type checking
- **[Pytest](https://docs.pytest.org/)** with coverage for testing
- **GitHub Actions** CI/CD with auto-release on merge to main

## Quick Start

\`\`\`bash
git clone https://github.com/${GITHUB_REPO}.git
cd ${KEBAB_NAME}
uv sync
uv run pytest -v --cov
\`\`\`

## Next Steps

- [API Reference](api.md) — auto-generated documentation for all public functions
DOCS_INDEX_EOF

# Remove init.sh from project structure diagrams
sedi '/init\.sh.*Interactive template/d' README.md
sedi '/init\.sh.*Interactive project/d' CLAUDE.md

# Remove init.sh references from docs/publishing.md
sedi "s|run \`init.sh\` with \`--pypi\`, or manually|manually|" docs/publishing.md
sedi "s|has been updated by \`init.sh\` with|contains|" docs/publishing.md

# Remove init.sh reference from README publishing section
sedi "s|Run \`\./scripts/init\.sh --pypi\` to enable publishing (or uncomment|Uncomment|" README.md
sedi "s|the \`PYPI-START\`/\`PYPI-END\` block in \`release\.yml\` manually)\.|the \`PYPI-START\`/\`PYPI-END\` block in \`release.yml\`.|" README.md

# Remove init.sh reference from project structure diagrams
sedi "s|Apache-2.0 license (configurable via init.sh)|${LICENSE_SPDX} license|" README.md
sedi "s|Apache-2.0 license (configurable via init.sh)|${LICENSE_SPDX} license|" CLAUDE.md

# Strip template-only content from CLAUDE.md
# Use ENVIRON[] instead of -v to avoid awk interpreting backslash escapes
# in user-provided DESCRIPTION (e.g. \t, \n in "C:\temp" or "\d+").
KEBAB_NAME="${KEBAB_NAME}" DESCRIPTION="${DESCRIPTION}" LICENSE_SPDX="${LICENSE_SPDX}" \
awk '
/<!-- TEMPLATE-ONLY-START -->/ {
    skip = 1
    printf "**%s** — %s. Uses uv, Ruff, Pyright, and pre-commit\n", ENVIRON["KEBAB_NAME"], ENVIRON["DESCRIPTION"]
    printf "hooks. Licensed %s.\n", ENVIRON["LICENSE_SPDX"]
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
    if uv lock 2>/dev/null; then
        ok "uv.lock regenerated."
    else
        warn "uv lock failed. Run 'uv lock' manually to diagnose."
        VALIDATION_OK=false
    fi
else
    warn "uv not found. Run 'uv lock' manually after installing uv."
fi

# ---------------------------------------------------------------------------
# 13. Post-init validation
# ---------------------------------------------------------------------------

info "Validating initialized project..."

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
    --include='*.md' --include='*.cfg' --include='*.json' --include='*.sh' \
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
    sedi '/test_init_flags/d' CLAUDE.md
    sedi '/template\/.*# Template tests/d' README.md
    sedi '/test_template_structure.*Verifies template/d' README.md
    sedi '/test_init_license.*Integration tests/d' README.md

    ok "Template tests removed."
fi

# Remove Docker E2E test suite (template-only infrastructure)
if [[ -d "tests/e2e" ]]; then
    rm -rf tests/e2e
    rm -f .dockerignore
    rm -f .github/workflows/e2e.yml

    # Remove e2e/ references from documentation
    sedi '/e2e\/.*# Docker-based/d' CLAUDE.md
    sedi '/Dockerfile.*# Parameterized base/d' CLAUDE.md
    sedi '/verify-project\.sh.*# Container-side/d' CLAUDE.md
    sedi '/run-e2e\.sh.*# Host-side/d' CLAUDE.md
    sedi '/e2e\.yml.*# E2E/d' CLAUDE.md
    sedi '/\.dockerignore.*# Docker build/d' CLAUDE.md
    sedi '/run-e2e\.sh/d' CLAUDE.md

    # Remove E2E section from README.md (from header to next ### heading)
    awk '/^### On Push to Main and Pull Request.*e2e/{skip=1; next} /^###/{skip=0} !skip{print}' README.md > README.md.tmp && mv README.md.tmp README.md

    ok "E2E test suite removed."
fi

# Remove "Template Tests" section from .claude/rules/testing.md
if [[ -f .claude/rules/testing.md ]]; then
    sedi '/^## Template Tests$/,/^are automatically removed when/d' .claude/rules/testing.md
fi

# Rewrite "License Headers" section in .claude/rules/code-style.md
if [[ -f .claude/rules/code-style.md ]]; then
    if [[ "$LICENSE_KEY_LOWER" != "none" ]]; then
        python3 -c "
content = open('.claude/rules/code-style.md').read()
old_section = '''## License Headers

- After running \`init.sh\` with a license selection, all \`.py\` files
  will have SPDX license headers and an \`insert-license\` pre-commit
  hook enforces them on new files.
- Place after shebang (if present), before module docstring.
- Format:
  \`\`\`python
  # Copyright YYYY Author Name
  # SPDX-License-Identifier: LICENSE-ID
  \`\`\`
- The template repo itself does not ship with headers — they are
  generated by \`init.sh\` based on the selected license.'''
new_section = '''## License Headers

- All \`.py\` files have SPDX license headers. The \`insert-license\`
  pre-commit hook enforces them on new files.
- Place after shebang (if present), before module docstring.
- Format:
  \`\`\`python
  # Copyright YYYY Author Name
  # SPDX-License-Identifier: LICENSE-ID
  \`\`\`'''
content = content.replace(old_section, new_section)
open('.claude/rules/code-style.md', 'w').write(content)
"
    else
        python3 -c "
content = open('.claude/rules/code-style.md').read()
old_section = '''## License Headers

- After running \`init.sh\` with a license selection, all \`.py\` files
  will have SPDX license headers and an \`insert-license\` pre-commit
  hook enforces them on new files.
- Place after shebang (if present), before module docstring.
- Format:
  \`\`\`python
  # Copyright YYYY Author Name
  # SPDX-License-Identifier: LICENSE-ID
  \`\`\`
- The template repo itself does not ship with headers — they are
  generated by \`init.sh\` based on the selected license.'''
new_section = '''## License Headers

- Add SPDX license headers to all \`.py\` files when applicable.
- Place after shebang (if present), before module docstring.
- Format:
  \`\`\`python
  # Copyright YYYY Author Name
  # SPDX-License-Identifier: LICENSE-ID
  \`\`\`'''
content = content.replace(old_section, new_section)
open('.claude/rules/code-style.md', 'w').write(content)
"
    fi
fi

# ---------------------------------------------------------------------------
# 15. Summary
# ---------------------------------------------------------------------------

echo ""
if [[ "$VALIDATION_OK" == "true" ]]; then
    ok "Project initialized successfully!"
else
    warn "Project initialized with warnings (see above)."
    exit 1
fi
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
