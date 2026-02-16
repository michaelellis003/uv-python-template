ARG BASE_IMAGE=python:3.13-slim
FROM ${BASE_IMAGE}

# Install system deps (detect Alpine vs Debian)
RUN if command -v apk > /dev/null 2>&1; then \
        apk add --no-cache bash curl git openssh; \
    else \
        apt-get update && apt-get install -y --no-install-recommends \
            curl git ca-certificates libatomic1 && \
        rm -rf /var/lib/apt/lists/*; \
    fi

# Install uv
# Keep version in sync with .pre-commit-config.yaml (uv-pre-commit rev).
COPY --from=ghcr.io/astral-sh/uv:0.7.12 /uv /uvx /usr/local/bin/

# Configure git (needed for pre-commit and init validation)
RUN git config --global user.email "e2e@test.com" && \
    git config --global user.name "E2E Test" && \
    git config --global init.defaultBranch main

# Copy template + verification script
WORKDIR /workspace
COPY . /workspace/template/
COPY tests/e2e/verify-project.sh /usr/local/bin/verify-project.sh
RUN chmod +x /usr/local/bin/verify-project.sh

ENTRYPOINT ["verify-project.sh"]
CMD ["mit"]
