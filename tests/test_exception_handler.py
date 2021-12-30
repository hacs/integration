# pylint: disable=missing-function-docstring, missing-module-docstring
from aiogithubapi import (
    GitHubAuthenticationException,
    GitHubNotModifiedException,
    GitHubRatelimitException,
)
from aiogithubapi.exceptions import GitHubException
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsDisabledReason
from custom_components.hacs.exceptions import HacsException


def test_exception_handler_githubauthenticationexception(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not hacs.system.disabled

    try:
        raise GitHubAuthenticationException()
    except BaseException as exception:
        hacs.exception_handler(exception)

    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.INVALID_TOKEN
    assert "GitHub authentication failed" in caplog.text


def test_exception_handler_githubratelimitexception(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert not hacs.system.disabled

    try:
        raise GitHubRatelimitException()
    except BaseException as exception:
        hacs.exception_handler(exception)

    assert hacs.system.disabled
    assert hacs.system.disabled_reason == HacsDisabledReason.RATE_LIMIT
    assert "GitHub API ratelimited" in caplog.text


def test_exception_handler_githubnotmodifiedexception(hacs: HacsBase) -> None:
    try:
        raise GitHubNotModifiedException()
    except BaseException as exception:
        with pytest.raises(GitHubNotModifiedException):
            hacs.exception_handler(exception)


def test_exception_handler_githubexception(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
) -> None:
    try:
        raise GitHubException()
    except BaseException as exception:
        with pytest.raises(HacsException):
            hacs.exception_handler(exception)
            assert "GitHub API error" in caplog.text


def test_exception_handler_baseexception(hacs: HacsBase) -> None:
    try:
        raise BaseException()
    except BaseException as exception:
        with pytest.raises(HacsException):
            hacs.exception_handler(exception)
