#!/usr/bin/env bash
# run-e2e.sh — host-side orchestrator for Docker-based E2E tests
#
# Usage:
#   ./tests/e2e/run-e2e.sh              # Full matrix (4 images x 2 licenses)
#   ./tests/e2e/run-e2e.sh --quick      # python:3.13-slim only (2 runs)
#   ./tests/e2e/run-e2e.sh --image python:3.13-alpine --license mit
#
# Requires: Docker running locally

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# Default full matrix
IMAGES=(
    "python:3.10-slim"
    "python:3.12-slim"
    "python:3.13-slim"
    "python:3.13-alpine"
)
LICENSES=("mit" "none")

SINGLE_IMAGE=""
SINGLE_LICENSE=""
QUICK=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick)
            QUICK=true
            shift
            ;;
        --image)
            SINGLE_IMAGE="$2"
            shift 2
            ;;
        --license)
            SINGLE_LICENSE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --quick              Run python:3.13-slim only (2 runs)"
            echo "  --image IMAGE        Run a single base image"
            echo "  --license LICENSE    Run a single license (mit, none, etc.)"
            echo "  --help, -h           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Apply filters
if [[ "$QUICK" == "true" ]]; then
    IMAGES=("python:3.13-slim")
fi

if [[ -n "$SINGLE_IMAGE" ]]; then
    IMAGES=("$SINGLE_IMAGE")
fi

if [[ -n "$SINGLE_LICENSE" ]]; then
    LICENSES=("$SINGLE_LICENSE")
fi

# ---------------------------------------------------------------------------
# Check Docker
# ---------------------------------------------------------------------------

if ! command -v docker &>/dev/null; then
    printf "${RED}error:${NC} Docker is not installed or not in PATH.\n"
    exit 1
fi

if ! docker ps &>/dev/null 2>&1; then
    printf "${RED}error:${NC} Docker daemon is not running.\n"
    exit 1
fi

# ---------------------------------------------------------------------------
# Build and run
# ---------------------------------------------------------------------------

RESULTS=()
TOTAL=0
PASSED=0
FAILED=0

# Convert image name to a safe Docker tag
image_to_tag() {
    echo "$1" | tr ':/' '-'
}

printf "\n${BOLD}Docker E2E Test Suite${NC}\n"
printf "=====================\n"
printf "Images:   %s\n" "${IMAGES[*]}"
printf "Licenses: %s\n" "${LICENSES[*]}"
printf "Total:    %d runs\n\n" "$(( ${#IMAGES[@]} * ${#LICENSES[@]} ))"

for IMAGE in "${IMAGES[@]}"; do
    TAG="e2e-$(image_to_tag "$IMAGE")"

    printf "${CYAN}==> Building image: %s (tag: %s)${NC}\n" "$IMAGE" "$TAG"
    if ! docker build \
        --build-arg "BASE_IMAGE=$IMAGE" \
        -t "$TAG" \
        -f "$REPO_ROOT/tests/e2e/Dockerfile" \
        "$REPO_ROOT" 2>&1; then
        printf "${RED}  Build failed for %s${NC}\n" "$IMAGE"
        for LICENSE in "${LICENSES[@]}"; do
            TOTAL=$((TOTAL + 1))
            FAILED=$((FAILED + 1))
            RESULTS+=("FAIL|$IMAGE|$LICENSE|build-failed")
        done
        continue
    fi
    printf "${GREEN}  Build succeeded${NC}\n\n"

    for LICENSE in "${LICENSES[@]}"; do
        TOTAL=$((TOTAL + 1))
        COMBO="$IMAGE + license=$LICENSE"

        printf "${CYAN}==> Running: %s${NC}\n" "$COMBO"
        if docker run --rm "$TAG" "$LICENSE" 2>&1; then
            PASSED=$((PASSED + 1))
            RESULTS+=("PASS|$IMAGE|$LICENSE|")
            printf "${GREEN}  PASSED: %s${NC}\n\n" "$COMBO"
        else
            FAILED=$((FAILED + 1))
            RESULTS+=("FAIL|$IMAGE|$LICENSE|")
            printf "${RED}  FAILED: %s${NC}\n\n" "$COMBO"
        fi
    done
done

# ---------------------------------------------------------------------------
# Summary table
# ---------------------------------------------------------------------------

printf "\n${BOLD}%-6s  %-25s  %-10s${NC}\n" "Status" "Image" "License"
printf "%-6s  %-25s  %-10s\n" "------" "-------------------------" "----------"

for RESULT in "${RESULTS[@]}"; do
    IFS='|' read -r STATUS IMAGE LICENSE NOTE <<< "$RESULT"
    if [[ "$STATUS" == "PASS" ]]; then
        COLOR="$GREEN"
    else
        COLOR="$RED"
    fi
    printf "${COLOR}%-6s${NC}  %-25s  %-10s" "$STATUS" "$IMAGE" "$LICENSE"
    if [[ -n "$NOTE" ]]; then
        printf "  ${YELLOW}(%s)${NC}" "$NOTE"
    fi
    printf "\n"
done

printf "\n${BOLD}Total: %d  Passed: %d  Failed: %d${NC}\n\n" "$TOTAL" "$PASSED" "$FAILED"

if [[ "$FAILED" -gt 0 ]]; then
    printf "${RED}${BOLD}SOME E2E TESTS FAILED${NC}\n\n"
    exit 1
else
    printf "${GREEN}${BOLD}ALL E2E TESTS PASSED${NC}\n\n"
    exit 0
fi
