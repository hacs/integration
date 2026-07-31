"""Tests for specific wake word repository implementations."""

import pytest

from homeassistant.core import ServiceCall

from custom_components.hacs.exceptions import HacsException


async def _stub_common_validate(repository):
    """Replace common_validate so validate_repository can run in isolation."""

    async def _noop(*_, **__):
        return None

    repository.common_validate = _noop


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


async def test_validate_repository_requires_manifest_and_model(repository_wake_word):
    """A compliant repository provides both a manifest and a model."""
    await _stub_common_validate(repository_wake_word)
    repository_wake_word.treefiles = [
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
    ]

    assert await repository_wake_word.validate_repository()


async def test_validate_repository_missing_manifest(repository_wake_word):
    """A model with no config manifest is not compliant (HA loads manifests)."""
    await _stub_common_validate(repository_wake_word)
    repository_wake_word.treefiles = ["custom_wake_words/my_wake_word.tflite"]

    with pytest.raises(HacsException):
        await repository_wake_word.validate_repository()


async def test_validate_repository_missing_model(repository_wake_word):
    """A manifest with no model is not compliant."""
    await _stub_common_validate(repository_wake_word)
    repository_wake_word.treefiles = ["custom_wake_words/my_wake_word.json"]

    with pytest.raises(HacsException):
        await repository_wake_word.validate_repository()


@pytest.mark.parametrize("hook", ["async_post_installation", "async_post_uninstall"])
async def test_reloads_custom_wake_words(repository_wake_word, hook):
    """Install/uninstall ask esphome to rescan the wake word directory."""
    hass = repository_wake_word.hacs.hass
    calls: list[ServiceCall] = []

    async def _handler(call: ServiceCall) -> None:
        calls.append(call)

    hass.services.async_register("esphome", "reload_custom_wake_words", _handler)

    await getattr(repository_wake_word, hook)()
    await hass.async_block_till_done()

    assert len(calls) == 1


@pytest.mark.parametrize("hook", ["async_post_installation", "async_post_uninstall"])
async def test_reload_noop_without_esphome(repository_wake_word, hook):
    """When esphome is not loaded the hooks are a no-op and do not raise."""
    hass = repository_wake_word.hacs.hass
    assert not hass.services.has_service("esphome", "reload_custom_wake_words")

    # Should not raise.
    await getattr(repository_wake_word, hook)()
