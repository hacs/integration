"""Tests for specific wake word repository implementations."""


def test_localpath_uses_full_name(repository_wake_word):
    """The install path is namespaced by the full name (owner/repo)."""
    config_path = repository_wake_word.hacs.core.config_path
    repository_wake_word.data.full_name = "octocat/okay_nabu"

    assert (
        repository_wake_word.localpath == f"{config_path}/custom_wake_words/octocat/okay_nabu"
    )


def test_localpath_deconflicts_same_repo_name_different_owner(repository_wake_word):
    """Two repos sharing a repo name but different owners must not collide."""
    repository_wake_word.data.full_name = "alice/okay_nabu"
    alice_path = repository_wake_word.localpath

    repository_wake_word.data.full_name = "bob/okay_nabu"
    bob_path = repository_wake_word.localpath

    assert alice_path != bob_path
