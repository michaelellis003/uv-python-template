import python_package_template
from python_package_template import __version__


def test_version_is_accessible():
    """Test that __version__ is a non-empty string."""
    assert isinstance(__version__, str)
    assert __version__ != ''


def test_public_api_exports_all_expected_names():
    """Test that __all__ contains exactly the expected public API."""
    expected = ['__version__', 'add', 'hello', 'multiply', 'subtract']
    assert sorted(python_package_template.__all__) == sorted(expected)
