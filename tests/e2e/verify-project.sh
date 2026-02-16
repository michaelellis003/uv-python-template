#!/usr/bin/env bash
# verify-project.sh — runs inside the Docker container
#
# Copies the template, runs init.sh, then verifies the initialized
# project actually works: uv sync, pytest, import, build, pre-commit.
#
# Usage: verify-project.sh <license>
#   license: SPDX key (e.g. "mit") or "none" to skip license setup

set -euo pipefail

LICENSE="${1:-mit}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf "${GREEN}  PASS${NC} %s\n" "$1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf "${RED}  FAIL${NC} %s\n" "$1"
}

skip() {
    SKIP_COUNT=$((SKIP_COUNT + 1))
    printf "${YELLOW}  SKIP${NC} %s\n" "$1"
}

is_alpine() {
    [ -f /etc/alpine-release ]
}

# ---------------------------------------------------------------------------
# 1. Copy template to a working directory
# ---------------------------------------------------------------------------

printf "\n${BOLD}=== E2E Test: license=%s ===${NC}\n\n" "$LICENSE"

printf "${CYAN}==> Copying template...${NC}\n"
cp -r /workspace/template /workspace/project
cd /workspace/project

# ---------------------------------------------------------------------------
# 2. Run init.sh
# ---------------------------------------------------------------------------

printf "${CYAN}==> Running init.sh --license %s ...${NC}\n" "$LICENSE"

# init.sh with flags still prompts for: PyPI publishing + confirmation
printf 'n\ny\n' | bash ./scripts/init.sh \
    --name test-pkg \
    --author "E2E Tester" \
    --email "e2e@test.com" \
    --github-owner "e2e-org" \
    --description "E2E test project" \
    --license "$LICENSE"

# ---------------------------------------------------------------------------
# 3. Verify init.sh outputs
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Checking init.sh results...${NC}\n"

# Package directory was renamed
if [ -d "test_pkg" ]; then
    pass "Package directory renamed to test_pkg/"
else
    fail "Package directory test_pkg/ not found"
fi

# init.sh removed itself
if [ ! -f "scripts/init.sh" ]; then
    pass "init.sh self-deleted"
else
    fail "init.sh still exists"
fi

# Template tests removed
if [ ! -d "tests/template" ]; then
    pass "tests/template/ removed"
else
    fail "tests/template/ still exists"
fi

# E2E test suite removed
if [ ! -d "tests/e2e" ] && [ ! -f ".dockerignore" ] && [ ! -f ".github/workflows/e2e.yml" ]; then
    pass "E2E test suite removed"
else
    fail "E2E artifacts still exist"
fi

# CODEOWNERS updated
if grep -q "@e2e-org" .github/CODEOWNERS; then
    pass "CODEOWNERS updated to @e2e-org"
else
    fail "CODEOWNERS still has template author"
fi

# docs/index.md rewritten (no init.sh reference)
if ! grep -q 'init\.sh' docs/index.md 2>/dev/null; then
    pass "docs/index.md has no init.sh reference"
else
    fail "docs/index.md still references init.sh"
fi

# docs/publishing.md cleaned (no init.sh reference)
if ! grep -q 'init\.sh' docs/publishing.md 2>/dev/null; then
    pass "docs/publishing.md has no init.sh reference"
else
    fail "docs/publishing.md still references init.sh"
fi

# .claude/rules/testing.md has no "Template Tests" section
if ! grep -q 'Template Tests' .claude/rules/testing.md 2>/dev/null; then
    pass "testing.md Template Tests section removed"
else
    fail "testing.md still has Template Tests section"
fi

# .claude/rules/code-style.md has no init.sh reference
if ! grep -q 'init\.sh' .claude/rules/code-style.md 2>/dev/null; then
    pass "code-style.md has no init.sh reference"
else
    fail "code-style.md still references init.sh"
fi

# README.md has no init.sh reference (outside template-only markers, which are gone)
if ! grep -q 'init\.sh' README.md 2>/dev/null; then
    pass "README.md has no init.sh reference"
else
    fail "README.md still references init.sh"
fi

# Package name replaced in pyproject.toml
if grep -q "test_pkg" pyproject.toml; then
    pass "pyproject.toml references test_pkg"
else
    fail "pyproject.toml missing test_pkg reference"
fi

# License classifier updated (when license != none)
if [ "$LICENSE" != "none" ]; then
    if ! grep -q 'Apache Software License' pyproject.toml; then
        pass "License classifier updated (Apache removed)"
    else
        fail "License classifier still says Apache"
    fi

    # Verify the correct classifier is present
    if grep -q 'MIT License' pyproject.toml; then
        pass "License classifier correct (MIT License)"
    else
        fail "Expected 'MIT License' classifier in pyproject.toml"
    fi
fi

# No stale template references in key files
STALE=$(grep -rl 'python_package_template\|python-package-template' \
    --include='*.py' --include='*.toml' --include='*.yml' \
    --include='*.yaml' --include='*.md' --include='*.json' \
    . 2>/dev/null \
    | grep -v '.git/' \
    | grep -v 'uv.lock' \
    || true)

if [ -z "$STALE" ]; then
    pass "No stale template references"
else
    fail "Stale template references in: $STALE"
fi

# License-specific checks
if [ "$LICENSE" != "none" ]; then
    if [ -f "LICENSE_HEADER" ]; then
        pass "LICENSE_HEADER exists"
    else
        fail "LICENSE_HEADER not found"
    fi
else
    if grep -q 'Apache-2.0' pyproject.toml; then
        pass "License unchanged (Apache-2.0)"
    else
        fail "License should be Apache-2.0 when --license none"
    fi
fi

# ---------------------------------------------------------------------------
# 4. uv sync
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Running uv sync...${NC}\n"
if uv sync 2>&1; then
    pass "uv sync"
else
    fail "uv sync"
fi

# ---------------------------------------------------------------------------
# 5. pytest
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Running pytest...${NC}\n"
if uv run pytest -v 2>&1; then
    pass "pytest"
else
    fail "pytest"
fi

# ---------------------------------------------------------------------------
# 6. Import check
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Checking import...${NC}\n"
if uv run python -c "import test_pkg; print('version:', test_pkg.__version__)" 2>&1; then
    pass "import test_pkg"
else
    fail "import test_pkg"
fi

# ---------------------------------------------------------------------------
# 7. uv build
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Building package...${NC}\n"
if uv build 2>&1; then
    pass "uv build"
else
    fail "uv build"
fi

# Verify wheel exists
if ls dist/*.whl 1>/dev/null 2>&1; then
    pass "wheel file exists"
else
    fail "wheel file not found in dist/"
fi

# ---------------------------------------------------------------------------
# 8. pre-commit (skip on Alpine — pyright needs glibc)
# ---------------------------------------------------------------------------

printf "\n${CYAN}==> Running pre-commit...${NC}\n"

if is_alpine; then
    skip "pre-commit (Alpine lacks glibc for pyright)"
else
    # Initialize git repo (pre-commit needs it)
    git init
    git add -A
    git commit -m "chore: initial commit"

    if uv run pre-commit run --all-files 2>&1; then
        pass "pre-commit"
    else
        # pre-commit often fixes files on first run; try again
        printf "${YELLOW}  Retrying pre-commit after auto-fixes...${NC}\n"
        git add -A
        if uv run pre-commit run --all-files 2>&1; then
            pass "pre-commit (after auto-fix)"
        else
            fail "pre-commit"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# 9. Summary
# ---------------------------------------------------------------------------

printf "\n${BOLD}=== Summary ===${NC}\n"
printf "  ${GREEN}Passed: %d${NC}\n" "$PASS_COUNT"
printf "  ${RED}Failed: %d${NC}\n" "$FAIL_COUNT"
printf "  ${YELLOW}Skipped: %d${NC}\n" "$SKIP_COUNT"
printf "\n"

if [ "$FAIL_COUNT" -gt 0 ]; then
    printf "${RED}${BOLD}E2E FAILED${NC}\n\n"
    exit 1
else
    printf "${GREEN}${BOLD}E2E PASSED${NC}\n\n"
    exit 0
fi
