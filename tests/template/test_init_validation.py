"""Unit tests for init.py pure validation and transformation functions.

These tests verify the validation rules, name transforms, and TOML
escaping without touching the filesystem or running prompts.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load scripts/init.py as a module via importlib (PEP 723 script)
# ---------------------------------------------------------------------------

_INIT_SCRIPT = (
    Path(__file__).resolve().parent.parent.parent / 'scripts' / 'init.py'
)


@pytest.fixture(scope='module')
def init_mod():
    """Import scripts/init.py as a Python module."""
    spec = importlib.util.spec_from_file_location('init', _INIT_SCRIPT)
    assert spec is not None, f'Cannot load {_INIT_SCRIPT}'
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Temporarily add to sys.modules so relative imports work
    sys.modules['init'] = mod
    spec.loader.exec_module(mod)
    yield mod
    sys.modules.pop('init', None)


# ===================================================================
# to_snake
# ===================================================================


class TestToSnake:
    """Tests for to_snake name transform."""

    def test_to_snake_converts_hyphens_to_underscores(self, init_mod):
        """Test that to_snake converts hyphens to underscores."""
        assert init_mod.to_snake('my-cool-package') == 'my_cool_package'

    def test_to_snake_preserves_underscores(self, init_mod):
        """Test that to_snake leaves underscores unchanged."""
        assert init_mod.to_snake('my_cool_package') == 'my_cool_package'

    def test_to_snake_handles_single_word(self, init_mod):
        """Test that to_snake handles a single word without separators."""
        assert init_mod.to_snake('package') == 'package'


# ===================================================================
# to_kebab
# ===================================================================


class TestToKebab:
    """Tests for to_kebab name transform."""

    def test_to_kebab_converts_underscores_to_hyphens(self, init_mod):
        """Test that to_kebab converts underscores to hyphens."""
        assert init_mod.to_kebab('my_cool_package') == 'my-cool-package'

    def test_to_kebab_preserves_hyphens(self, init_mod):
        """Test that to_kebab leaves hyphens unchanged."""
        assert init_mod.to_kebab('my-cool-package') == 'my-cool-package'

    def test_to_kebab_handles_single_word(self, init_mod):
        """Test that to_kebab handles a single word without separators."""
        assert init_mod.to_kebab('package') == 'package'


# ===================================================================
# to_title
# ===================================================================


class TestToTitle:
    """Tests for to_title name transform."""

    def test_to_title_converts_kebab_to_title_case(self, init_mod):
        """Test that to_title converts kebab-case to Title Case."""
        assert init_mod.to_title('my-cool-package') == 'My Cool Package'

    def test_to_title_converts_snake_to_title_case(self, init_mod):
        """Test that to_title converts snake_case to Title Case."""
        assert init_mod.to_title('my_cool_package') == 'My Cool Package'

    def test_to_title_handles_single_word(self, init_mod):
        """Test that to_title capitalizes a single word."""
        assert init_mod.to_title('package') == 'Package'


# ===================================================================
# escape_toml_string
# ===================================================================


class TestEscapeTomlString:
    """Tests for escape_toml_string."""

    def test_escape_toml_string_escapes_backslash(self, init_mod):
        """Test that backslashes are doubled."""
        assert init_mod.escape_toml_string(r'C:\new') == 'C:\\\\new'

    def test_escape_toml_string_escapes_double_quotes(self, init_mod):
        """Test that double quotes are escaped."""
        assert init_mod.escape_toml_string('a "b" c') == 'a \\"b\\" c'

    def test_escape_toml_string_plain_text_unchanged(self, init_mod):
        """Test that plain text passes through unchanged."""
        assert init_mod.escape_toml_string('hello world') == 'hello world'

    def test_escape_toml_string_backslash_and_quotes(self, init_mod):
        """Test that backslash is escaped before quotes."""
        result = init_mod.escape_toml_string(r'path \"quoted\"')
        assert result == 'path \\\\\\"quoted\\\\\\"'


# ===================================================================
# validate_name
# ===================================================================


class TestValidateName:
    """Tests for validate_name."""

    def test_validate_name_valid_kebab_passes(self, init_mod):
        """Test that a valid kebab-case name passes validation."""
        init_mod.validate_name('my-cool-package')

    def test_validate_name_valid_snake_passes(self, init_mod):
        """Test that a valid snake_case name passes validation."""
        init_mod.validate_name('my_cool_package')

    def test_validate_name_rejects_uppercase(self, init_mod):
        """Test that uppercase letters are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('MyPackage')

    def test_validate_name_rejects_starts_with_digit(self, init_mod):
        """Test that names starting with a digit are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('1package')

    def test_validate_name_rejects_template_default_kebab(self, init_mod):
        """Test that the template default name is rejected."""
        with pytest.raises(ValueError, match='template default'):
            init_mod.validate_name('python-package-template')

    def test_validate_name_rejects_template_default_snake(self, init_mod):
        """Test that the template default snake name is rejected."""
        with pytest.raises(ValueError, match='template default'):
            init_mod.validate_name('python_package_template')

    def test_validate_name_rejects_stdlib_shadow(self, init_mod):
        """Test that names shadowing stdlib modules are rejected."""
        with pytest.raises(ValueError, match='shadow'):
            init_mod.validate_name('json')

    def test_validate_name_rejects_stdlib_shadow_with_underscore(
        self, init_mod
    ):
        """Test that snake names that shadow stdlib are rejected."""
        with pytest.raises(ValueError, match='shadow'):
            init_mod.validate_name('base64')

    def test_validate_name_rejects_spaces(self, init_mod):
        """Test that names with spaces are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('my package')

    def test_validate_name_rejects_special_characters(self, init_mod):
        """Test that names with special characters are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('my@package')

    def test_validate_name_rejects_trailing_hyphen(self, init_mod):
        """Test that names ending with a hyphen are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('my-pkg-')

    def test_validate_name_rejects_trailing_underscore(self, init_mod):
        """Test that names ending with an underscore are rejected."""
        with pytest.raises(ValueError, match='Invalid package name'):
            init_mod.validate_name('my_pkg_')

    def test_validate_name_single_char_passes(self, init_mod):
        """Test that a single lowercase letter is a valid name."""
        init_mod.validate_name('a')


# ===================================================================
# validate_email
# ===================================================================


class TestValidateEmail:
    """Tests for validate_email."""

    def test_validate_email_valid_address_passes(self, init_mod):
        """Test that a valid email passes validation."""
        init_mod.validate_email('user@example.com')

    def test_validate_email_rejects_missing_at(self, init_mod):
        """Test that an email without @ is rejected."""
        with pytest.raises(ValueError, match='@'):
            init_mod.validate_email('userexample.com')

    def test_validate_email_rejects_multiline(self, init_mod):
        """Test that multiline email is rejected."""
        with pytest.raises(ValueError, match='single line'):
            init_mod.validate_email('user@example.com\nevil@evil.com')


# ===================================================================
# validate_github_owner
# ===================================================================


class TestValidateGithubOwner:
    """Tests for validate_github_owner."""

    def test_validate_github_owner_valid_name_passes(self, init_mod):
        """Test that a valid GitHub username passes."""
        init_mod.validate_github_owner('my-org')

    def test_validate_github_owner_alphanumeric_passes(self, init_mod):
        """Test that a pure alphanumeric name passes."""
        init_mod.validate_github_owner('myorg123')

    def test_validate_github_owner_single_char_passes(self, init_mod):
        """Test that a single character passes."""
        init_mod.validate_github_owner('a')

    def test_validate_github_owner_rejects_leading_hyphen(self, init_mod):
        """Test that a leading hyphen is rejected."""
        with pytest.raises(ValueError, match='Invalid GitHub owner'):
            init_mod.validate_github_owner('-my-org')

    def test_validate_github_owner_rejects_trailing_hyphen(self, init_mod):
        """Test that a trailing hyphen is rejected."""
        with pytest.raises(ValueError, match='Invalid GitHub owner'):
            init_mod.validate_github_owner('my-org-')

    def test_validate_github_owner_rejects_spaces(self, init_mod):
        """Test that spaces are rejected."""
        with pytest.raises(ValueError, match='Invalid GitHub owner'):
            init_mod.validate_github_owner('My Awesome Org!')

    def test_validate_github_owner_rejects_special_chars(self, init_mod):
        """Test that special characters are rejected."""
        with pytest.raises(ValueError, match='Invalid GitHub owner'):
            init_mod.validate_github_owner('org@name')


# ===================================================================
# validate_author_name
# ===================================================================


class TestValidateAuthorName:
    """Tests for validate_author_name."""

    def test_validate_author_name_valid_passes(self, init_mod):
        """Test that a valid author name passes."""
        init_mod.validate_author_name('Jane Smith')

    def test_validate_author_name_rejects_multiline(self, init_mod):
        """Test that a multiline author name is rejected."""
        with pytest.raises(ValueError, match='single line'):
            init_mod.validate_author_name('Jane\nSmith')

    def test_validate_author_name_allows_unicode(self, init_mod):
        """Test that unicode characters are allowed."""
        init_mod.validate_author_name('José García')

    def test_validate_author_name_allows_special_chars(self, init_mod):
        """Test that special chars (apostrophe, etc.) are allowed."""
        init_mod.validate_author_name("O'Brien-Smith")


# ===================================================================
# validate_description
# ===================================================================


class TestValidateDescription:
    """Tests for validate_description."""

    def test_validate_description_valid_passes(self, init_mod):
        """Test that a valid description passes."""
        init_mod.validate_description('A great package')

    def test_validate_description_rejects_empty(self, init_mod):
        """Test that an empty description is rejected."""
        with pytest.raises(ValueError, match='empty'):
            init_mod.validate_description('')

    def test_validate_description_rejects_whitespace_only(self, init_mod):
        """Test that whitespace-only description is rejected."""
        with pytest.raises(ValueError, match='empty'):
            init_mod.validate_description('   ')

    def test_validate_description_rejects_multiline(self, init_mod):
        """Test that a multiline description is rejected."""
        with pytest.raises(ValueError, match='single line'):
            init_mod.validate_description('line one\nline two')


# ===================================================================
# ProjectConfig dataclass
# ===================================================================


class TestProjectConfig:
    """Tests for ProjectConfig dataclass."""

    def test_project_config_stores_fields(self, init_mod):
        """Test that ProjectConfig stores all fields correctly."""
        cfg = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane Smith',
            email='jane@example.com',
            github_owner='janesmith',
            description='A package',
            license_key='mit',
            enable_pypi=False,
        )
        assert cfg.name == 'my-pkg'
        assert cfg.snake_name == 'my_pkg'
        assert cfg.kebab_name == 'my-pkg'
        assert cfg.title_name == 'My Pkg'
        assert cfg.github_repo == 'janesmith/my-pkg'
        assert cfg.author == 'Jane Smith'
        assert cfg.email == 'jane@example.com'
        assert cfg.github_owner == 'janesmith'
        assert cfg.description == 'A package'
        assert cfg.license_key == 'mit'
        assert cfg.enable_pypi is False

    def test_project_config_is_frozen(self, init_mod):
        """Test that ProjectConfig is immutable."""
        cfg = init_mod.ProjectConfig(
            name='my-pkg',
            author='Jane',
            email='j@e.com',
            github_owner='jane',
            description='Pkg',
            license_key='mit',
            enable_pypi=False,
        )
        with pytest.raises(AttributeError):
            cfg.name = 'other'  # type: ignore[misc]


# ===================================================================
# LicenseInfo dataclass
# ===================================================================


class TestLicenseInfo:
    """Tests for LicenseInfo dataclass."""

    def test_license_info_stores_fields(self, init_mod):
        """Test that LicenseInfo stores all fields."""
        info = init_mod.LicenseInfo(
            key='mit',
            name='MIT License',
            spdx_id='MIT',
        )
        assert info.key == 'mit'
        assert info.name == 'MIT License'
        assert info.spdx_id == 'MIT'

    def test_license_info_is_frozen(self, init_mod):
        """Test that LicenseInfo is immutable."""
        info = init_mod.LicenseInfo(
            key='mit',
            name='MIT License',
            spdx_id='MIT',
        )
        with pytest.raises(AttributeError):
            info.key = 'apache-2.0'  # type: ignore[misc]


# ===================================================================
# Constants
# ===================================================================


class TestConstants:
    """Tests for module-level constants."""

    def test_stdlib_names_contains_json(self, init_mod):
        """Test that STDLIB_NAMES includes common modules."""
        assert 'json' in init_mod.STDLIB_NAMES
        assert 'os' in init_mod.STDLIB_NAMES
        assert 'sys' in init_mod.STDLIB_NAMES

    def test_stdlib_names_excludes_nonexistent(self, init_mod):
        """Test that STDLIB_NAMES does not contain random strings."""
        assert 'my_cool_package' not in init_mod.STDLIB_NAMES

    def test_spdx_map_maps_mit(self, init_mod):
        """Test that SPDX_MAP maps 'mit' to 'MIT'."""
        assert init_mod.SPDX_MAP['mit'] == 'MIT'

    def test_spdx_map_maps_apache(self, init_mod):
        """Test that SPDX_MAP maps 'apache-2.0' to 'Apache-2.0'."""
        assert init_mod.SPDX_MAP['apache-2.0'] == 'Apache-2.0'

    def test_classifier_map_maps_mit(self, init_mod):
        """Test that CLASSIFIER_MAP maps MIT to the trove string."""
        assert 'MIT License' in init_mod.CLASSIFIER_MAP['MIT']

    def test_offline_licenses_is_nonempty(self, init_mod):
        """Test that OFFLINE_LICENSES has entries."""
        assert len(init_mod.OFFLINE_LICENSES) > 0

    def test_offline_licenses_has_mit(self, init_mod):
        """Test that OFFLINE_LICENSES includes MIT."""
        keys = [lic.key for lic in init_mod.OFFLINE_LICENSES]
        assert 'mit' in keys


# ===================================================================
# spdx_id_for_key helper
# ===================================================================


class TestSpdxIdForKey:
    """Tests for spdx_id_for_key helper."""

    def test_spdx_id_for_known_key(self, init_mod):
        """Test that known keys map correctly."""
        assert init_mod.spdx_id_for_key('mit') == 'MIT'
        assert init_mod.spdx_id_for_key('gpl-3.0') == 'GPL-3.0-only'

    def test_spdx_id_for_unknown_key_uppercases(self, init_mod):
        """Test that unknown keys get uppercased as fallback."""
        assert init_mod.spdx_id_for_key('custom-lic') == 'CUSTOM-LIC'


# ===================================================================
# classifier_for_spdx helper
# ===================================================================


class TestClassifierForSpdx:
    """Tests for classifier_for_spdx helper."""

    def test_classifier_for_known_spdx(self, init_mod):
        """Test that known SPDX IDs return classifier strings."""
        result = init_mod.classifier_for_spdx('MIT')
        assert result is not None
        assert 'MIT License' in result

    def test_classifier_for_unknown_spdx_returns_none(self, init_mod):
        """Test that unknown SPDX IDs return None."""
        assert init_mod.classifier_for_spdx('UNKNOWN-1.0') is None


# ===================================================================
# parse_args
# ===================================================================


class TestParseArgs:
    """Tests for parse_args."""

    def test_parse_args_all_flags(self, init_mod):
        """Test that all flags are parsed correctly."""
        args = init_mod.parse_args(
            [
                '--name',
                'my-pkg',
                '--author',
                'Jane Smith',
                '--email',
                'jane@example.com',
                '--github-owner',
                'janesmith',
                '--description',
                'A great package',
                '--license',
                'mit',
                '--pypi',
            ]
        )
        assert args.name == 'my-pkg'
        assert args.author == 'Jane Smith'
        assert args.email == 'jane@example.com'
        assert args.github_owner == 'janesmith'
        assert args.description == 'A great package'
        assert args.license == 'mit'
        assert args.pypi is True

    def test_parse_args_short_name_flag(self, init_mod):
        """Test that -n works as short form of --name."""
        args = init_mod.parse_args(['-n', 'my-pkg'])
        assert args.name == 'my-pkg'

    def test_parse_args_defaults_to_none(self, init_mod):
        """Test that unset flags default to None."""
        args = init_mod.parse_args([])
        assert args.name is None
        assert args.author is None
        assert args.email is None
        assert args.github_owner is None
        assert args.description is None
        assert args.license is None
        assert args.pypi is False

    def test_parse_args_pypi_flag_is_boolean(self, init_mod):
        """Test that --pypi takes no argument."""
        args = init_mod.parse_args(['--pypi'])
        assert args.pypi is True

    def test_parse_args_without_pypi(self, init_mod):
        """Test that pypi defaults to False."""
        args = init_mod.parse_args(['--name', 'test'])
        assert args.pypi is False
