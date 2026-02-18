"""Tests for pypkgkit.github module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from pypkgkit.github import (
    _build_ruleset_payload,
    check_gh_authenticated,
    check_gh_installed,
    check_git_installed,
    create_github_repo,
    detect_gh_owner,
    git_init,
    git_push,
    setup_github,
    setup_ruleset,
)


class TestCheckGitInstalled:
    """Test check_git_installed."""

    def test_returns_true_when_git_available(self):
        """Test that True is returned when git is found."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert check_git_installed() is True

    def test_returns_false_when_git_not_found(self):
        """Test that False is returned when git is missing."""
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=FileNotFoundError,
        ):
            assert check_git_installed() is False

    def test_returns_false_when_git_fails(self):
        """Test that False is returned when git --version fails."""
        mock_result = MagicMock(returncode=1)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert check_git_installed() is False


class TestCheckGhInstalled:
    """Test check_gh_installed."""

    def test_returns_true_when_gh_available(self):
        """Test that True is returned when gh is found."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert check_gh_installed() is True

    def test_returns_false_when_gh_not_found(self):
        """Test that False is returned when gh is missing."""
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=FileNotFoundError,
        ):
            assert check_gh_installed() is False


class TestCheckGhAuthenticated:
    """Test check_gh_authenticated."""

    def test_returns_true_when_authenticated(self):
        """Test that True is returned when gh is authenticated."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert check_gh_authenticated() is True

    def test_returns_false_when_not_authenticated(self):
        """Test that False is returned when gh is not authenticated."""
        mock_result = MagicMock(returncode=1)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert check_gh_authenticated() is False


class TestDetectGhOwner:
    """Test detect_gh_owner."""

    def test_returns_username_on_success(self):
        """Test that the GitHub username is returned."""
        mock_result = MagicMock(returncode=0, stdout='janesmith\n')
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert detect_gh_owner() == 'janesmith'

    def test_returns_none_on_failure(self):
        """Test that None is returned when detection fails."""
        mock_result = MagicMock(returncode=1, stdout='')
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert detect_gh_owner() is None

    def test_returns_none_on_empty_stdout(self):
        """Test that None is returned when stdout is empty."""
        mock_result = MagicMock(returncode=0, stdout='  \n')
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            assert detect_gh_owner() is None


class TestGitInit:
    """Test git_init."""

    def test_runs_three_commands_in_order(self, tmp_path: Path):
        """Test that git init, add, and commit are called."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            rc = git_init(tmp_path)

        assert rc == 0
        assert mock_run.call_count == 3
        cmds = [c[0][0] for c in mock_run.call_args_list]
        assert cmds[0] == ['git', 'init']
        assert cmds[1] == ['git', 'add', '.']
        assert cmds[2][:2] == ['git', 'commit']

    def test_returns_nonzero_on_init_failure(self, tmp_path: Path):
        """Test that failure in git init propagates."""
        mock_fail = MagicMock(returncode=128)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_fail,
        ):
            rc = git_init(tmp_path)

        assert rc == 128

    def test_returns_nonzero_on_commit_failure(self, tmp_path: Path):
        """Test that failure in git commit propagates."""
        results = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=1),
        ]
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=results,
        ):
            rc = git_init(tmp_path)

        assert rc == 1


class TestGitPush:
    """Test git_push."""

    def test_runs_push_command(self, tmp_path: Path):
        """Test that git push -u origin main is called."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            rc = git_push(tmp_path)

        assert rc == 0
        cmd = mock_run.call_args[0][0]
        assert cmd == ['git', 'push', '-u', 'origin', 'main']

    def test_returns_nonzero_on_failure(self, tmp_path: Path):
        """Test that push failure propagates."""
        mock_result = MagicMock(returncode=1)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            rc = git_push(tmp_path)

        assert rc == 1


class TestCreateGithubRepo:
    """Test create_github_repo."""

    def test_creates_public_repo_and_adds_remote(self, tmp_path: Path):
        """Test public repo creation and remote add."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            rc = create_github_repo(
                tmp_path,
                owner='jane',
                name='my-project',
            )

        assert rc == 0
        assert mock_run.call_count == 2
        create_cmd = mock_run.call_args_list[0][0][0]
        assert 'jane/my-project' in create_cmd
        assert '--public' in create_cmd
        remote_cmd = mock_run.call_args_list[1][0][0]
        assert remote_cmd[:3] == ['git', 'remote', 'add']
        assert 'https://github.com/jane/my-project.git' in remote_cmd

    def test_creates_private_repo(self, tmp_path: Path):
        """Test private repo creation."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            create_github_repo(
                tmp_path,
                owner='jane',
                name='my-project',
                private=True,
            )

        create_cmd = mock_run.call_args_list[0][0][0]
        assert '--private' in create_cmd

    def test_includes_description(self, tmp_path: Path):
        """Test description flag is passed."""
        mock_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ) as mock_run:
            create_github_repo(
                tmp_path,
                owner='jane',
                name='my-project',
                description='My awesome project',
            )

        create_cmd = mock_run.call_args_list[0][0][0]
        assert '--description' in create_cmd
        assert 'My awesome project' in create_cmd

    def test_returns_nonzero_on_create_failure(self, tmp_path: Path):
        """Test that repo creation failure propagates."""
        mock_result = MagicMock(returncode=1)
        with patch(
            'pypkgkit.github.subprocess.run',
            return_value=mock_result,
        ):
            rc = create_github_repo(tmp_path, owner='jane', name='my-project')

        assert rc == 1


class TestBuildRulesetPayload:
    """Test _build_ruleset_payload."""

    def test_default_payload_structure(self):
        """Test default ruleset has correct structure."""
        payload = _build_ruleset_payload()
        assert payload['name'] == 'main branch protection'
        assert payload['target'] == 'branch'
        assert payload['enforcement'] == 'active'
        assert payload['conditions']['ref_name']['include'] == [
            'refs/heads/main'
        ]

    def test_bypass_actors_includes_admin(self):
        """Test admin bypass is configured."""
        payload = _build_ruleset_payload()
        actors = payload['bypass_actors']
        assert len(actors) == 1
        assert actors[0]['actor_id'] == 5
        assert actors[0]['actor_type'] == 'RepositoryRole'

    def test_rules_include_required_types(self):
        """Test all required rule types are present."""
        payload = _build_ruleset_payload()
        rule_types = [r['type'] for r in payload['rules']]
        assert 'pull_request' in rule_types
        assert 'required_status_checks' in rule_types
        assert 'non_fast_forward' in rule_types
        assert 'deletion' in rule_types

    def test_ci_pass_status_check(self):
        """Test ci-pass is the required status check."""
        payload = _build_ruleset_payload()
        checks_rule = next(
            r
            for r in payload['rules']
            if r['type'] == 'required_status_checks'
        )
        contexts = [
            c['context']
            for c in checks_rule['parameters']['required_status_checks']
        ]
        assert 'ci-pass' in contexts

    def test_require_reviews_sets_count(self):
        """Test that require_reviews parameter is applied."""
        payload = _build_ruleset_payload(require_reviews=2)
        pr_rule = next(
            r for r in payload['rules'] if r['type'] == 'pull_request'
        )
        count = pr_rule['parameters']['required_approving_review_count']
        assert count == 2

    def test_default_review_count_is_zero(self):
        """Test that default review count is 0."""
        payload = _build_ruleset_payload()
        pr_rule = next(
            r for r in payload['rules'] if r['type'] == 'pull_request'
        )
        count = pr_rule['parameters']['required_approving_review_count']
        assert count == 0


class TestSetupRuleset:
    """Test setup_ruleset."""

    def test_creates_new_ruleset_via_post(self):
        """Test POST when no existing ruleset found."""
        list_result = MagicMock(returncode=0, stdout='')
        post_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=[list_result, post_result],
        ) as mock_run:
            rc = setup_ruleset(owner='jane', name='my-project')

        assert rc == 0
        post_cmd = mock_run.call_args_list[1][0][0]
        assert 'repos/jane/my-project/rulesets' in ' '.join(post_cmd)
        assert '--method' in post_cmd
        assert 'POST' in post_cmd

    def test_updates_existing_ruleset_via_put(self):
        """Test PUT when existing ruleset is found."""
        list_result = MagicMock(returncode=0, stdout='42\n')
        put_result = MagicMock(returncode=0)
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=[list_result, put_result],
        ) as mock_run:
            rc = setup_ruleset(owner='jane', name='my-project')

        assert rc == 0
        put_cmd = mock_run.call_args_list[1][0][0]
        assert 'repos/jane/my-project/rulesets/42' in ' '.join(put_cmd)
        assert 'PUT' in put_cmd

    def test_returns_nonzero_on_failure(self):
        """Test failure propagation."""
        list_result = MagicMock(returncode=0, stdout='')
        post_result = MagicMock(returncode=1)
        with patch(
            'pypkgkit.github.subprocess.run',
            side_effect=[list_result, post_result],
        ):
            rc = setup_ruleset(owner='jane', name='my-project')

        assert rc == 1


class TestSetupGithub:
    """Test setup_github orchestrator."""

    def test_full_pipeline_succeeds(self, tmp_path: Path):
        """Test full GitHub setup pipeline."""
        with (
            patch(
                'pypkgkit.github.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.create_github_repo',
                return_value=0,
            ),
            patch('pypkgkit.github.git_push', return_value=0),
            patch('pypkgkit.github.setup_ruleset', return_value=0),
        ):
            rc = setup_github(tmp_path, owner='jane', repo_name='my-project')

        assert rc == 0

    def test_fails_when_gh_not_installed(self, tmp_path: Path):
        """Test early failure when gh is missing."""
        with patch(
            'pypkgkit.github.check_gh_installed',
            return_value=False,
        ):
            rc = setup_github(tmp_path, owner='jane', repo_name='my-project')

        assert rc != 0

    def test_fails_when_gh_not_authenticated(self, tmp_path: Path):
        """Test early failure when gh is not authenticated."""
        with (
            patch(
                'pypkgkit.github.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.check_gh_authenticated',
                return_value=False,
            ),
        ):
            rc = setup_github(tmp_path, owner='jane', repo_name='my-project')

        assert rc != 0

    def test_fails_when_repo_creation_fails(self, tmp_path: Path):
        """Test failure when repo creation fails."""
        with (
            patch(
                'pypkgkit.github.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.create_github_repo',
                return_value=1,
            ),
        ):
            rc = setup_github(tmp_path, owner='jane', repo_name='my-project')

        assert rc != 0

    def test_fails_when_push_fails(self, tmp_path: Path):
        """Test failure when git push fails."""
        with (
            patch(
                'pypkgkit.github.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.create_github_repo',
                return_value=0,
            ),
            patch('pypkgkit.github.git_push', return_value=1),
        ):
            rc = setup_github(tmp_path, owner='jane', repo_name='my-project')

        assert rc != 0

    def test_passes_options_through(self, tmp_path: Path):
        """Test that private, description, reviews are passed."""
        with (
            patch(
                'pypkgkit.github.check_gh_installed',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.check_gh_authenticated',
                return_value=True,
            ),
            patch(
                'pypkgkit.github.create_github_repo',
                return_value=0,
            ) as mock_create,
            patch('pypkgkit.github.git_push', return_value=0),
            patch(
                'pypkgkit.github.setup_ruleset', return_value=0
            ) as mock_ruleset,
        ):
            setup_github(
                tmp_path,
                owner='jane',
                repo_name='my-project',
                description='Cool project',
                private=True,
                require_reviews=2,
            )

        mock_create.assert_called_once_with(
            tmp_path,
            owner='jane',
            name='my-project',
            description='Cool project',
            private=True,
        )
        mock_ruleset.assert_called_once_with(
            owner='jane',
            name='my-project',
            require_reviews=2,
        )
