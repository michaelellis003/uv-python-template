"""Shared test fixtures.

Add project-wide pytest fixtures here. They will be automatically
discovered by pytest and available to all test files.
"""

import pytest

import python_package_template


@pytest.fixture
def package():
    """Return the top-level package module for introspection."""
    return python_package_template
