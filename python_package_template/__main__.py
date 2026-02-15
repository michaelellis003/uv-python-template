"""Allow running the package with ``python -m python_package_template``."""

from python_package_template import __version__


def main() -> None:
    """Print package version."""
    print(f'python_package_template {__version__}')


if __name__ == '__main__':
    main()
