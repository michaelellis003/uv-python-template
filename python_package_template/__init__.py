"""This is the python_package_template package."""

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _version

from .main import add, hello, multiply, subtract  # re-export

try:
    __version__ = _version('python-package-template')
except _PackageNotFoundError:
    __version__ = '0.0.0'

__all__ = ['__version__', 'add', 'hello', 'multiply', 'subtract']
