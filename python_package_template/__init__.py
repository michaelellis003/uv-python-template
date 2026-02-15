"""This is the python_package_template package."""

from importlib.metadata import PackageNotFoundError, version

from .main import add, hello, multiply, subtract  # re-export

try:
    __version__ = version('python-package-template')
except PackageNotFoundError:
    __version__ = '0.0.0'

__all__ = ['__version__', 'add', 'hello', 'multiply', 'subtract']
