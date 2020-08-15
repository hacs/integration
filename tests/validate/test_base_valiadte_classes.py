from custom_components.hacs.validate.base import (
    ActionValidationBase,
    ValidationBase,
)
from tests.dummy_repository import dummy_repository_base


def test_validation_base(hass):
    base = ValidationBase(dummy_repository_base(hass))
    assert not base.action_only


def test_action_validation_base(hass):
    base = ActionValidationBase(dummy_repository_base(hass))
    assert base.action_only
