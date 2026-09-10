# pylint: disable=missing-module-docstring, missing-function-docstring
from homeassistant.helpers import issue_registry as ir
import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsCategory


async def test_hacs(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_id(None) is None

    repository.data.id = "1337"
    repository.data.category = "integration"
    repository.data.installed = True

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_id("1337").data.full_name == "test/test"
    assert hacs.repositories.get_by_id("1337").data.full_name_lower == "test/test"

    hacs.repositories = HacsRepositories()
    assert hacs.repositories.get_by_full_name(None) is None

    hacs.repositories.register(repository)
    assert hacs.repositories.get_by_full_name("test/test").data.id == "1337"
    assert hacs.repositories.is_registered(repository_id="1337")

    assert hacs.repositories.category_downloaded(category=HacsCategory.INTEGRATION)
    for category in [x for x in list(HacsCategory) if x != HacsCategory.INTEGRATION]:
        assert not hacs.repositories.category_downloaded(category=category)

    await hacs.async_process_queue()


async def test_add_remove_repository(hacs, repository, tmpdir):
    hacs.hass.config.config_dir = tmpdir

    repository.data.id = "0"
    hacs.repositories.register(repository)

    hacs.repositories.set_repository_id(repository, "42")

    # Once its set, it should never change
    with pytest.raises(ValueError):
        hacs.repositories.set_repository_id(repository, "30")

    # Safe to set it again
    hacs.repositories.set_repository_id(repository, "42")

    assert hacs.repositories.get_by_full_name("test/test") is repository
    assert hacs.repositories.get_by_id("42") is repository

    hacs.repositories.unregister(repository)
    assert hacs.repositories.get_by_full_name("test/test") is None
    assert hacs.repositories.get_by_id("42") is None

    # Verify second removal does not raise
    hacs.repositories.unregister(repository)


async def test_delete_stale_restart_issues(hacs):
    issue_registry = ir.async_get(hacs.hass)

    ir.async_create_issue(
        hass=hacs.hass,
        domain=DOMAIN,
        issue_id="restart_required_1337_tags/1.0.0",
        is_fixable=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key="restart_required",
    )
    ir.async_create_issue(
        hass=hacs.hass,
        domain=DOMAIN,
        issue_id="removed_1337",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="removed",
    )
    ir.async_create_issue(
        hass=hacs.hass,
        domain="other",
        issue_id="restart_required_1337_tags/1.0.0",
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="restart_required",
    )

    hacs.async_delete_stale_restart_issues()

    # The restart has already happened, so the issue is no longer relevant
    assert issue_registry.async_get_issue(DOMAIN, "restart_required_1337_tags/1.0.0") is None

    # Issues of other types, and issues from other domains, are left alone
    assert issue_registry.async_get_issue(DOMAIN, "removed_1337") is not None
    assert issue_registry.async_get_issue("other", "restart_required_1337_tags/1.0.0") is not None

    # Safe to run when there is nothing to delete
    hacs.async_delete_stale_restart_issues()
