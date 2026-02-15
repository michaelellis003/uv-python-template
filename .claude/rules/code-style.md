---
paths:
  - "python_package_template/**/*.py"
  - "tests/**/*.py"
---

# Code Style Rules

All code MUST conform to these standards enforced by Ruff and Pyright.

## Formatting (Ruff)

- **Line length:** 79 characters maximum
- **Indent:** 4 spaces (no tabs)
- **Quotes:** Single quotes everywhere
- **Target Python:** 3.10+

## Linting (Ruff)

Enabled rules: pyflakes (F), pycodestyle (E4/E7/E9/E501),
pep8-naming (N), pydocstyle (D), pyupgrade (UP),
flake8-bugbear (B), flake8-simplify (SIM), isort (I).

Tests (`tests/*`) are exempt from E501 (line length).

## Docstrings

- **Required** on all public modules, classes, and functions.
- Use **Google-style** convention.
- Include `Args` and `Returns` sections with types.

```python
def multiply(a: float, b: int) -> float:
    """Multiply a float by an integer.

    Args:
        a (float): The float number.
        b (int): The integer number.

    Returns:
        float: The product of the float and the integer.
    """
    return a * b
```

## Type Annotations

- All function parameters and return values MUST have type hints.
- Pyright enforces this (excludes `tests/` directory).

## Imports

- Public API re-exported from `python_package_template/__init__.py`
  using `__all__`.
- Import ordering managed by isort via Ruff.
- Use `from .module import name` for intra-package imports.
