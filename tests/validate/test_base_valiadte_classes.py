from custom_components.hacs.validate.base import (
    ActionValidationBase,
    ValidationBase,
)
from tests.dummy_repository import dummy_repository_base


def test_validation_base():
    base = ValidationBase(dummy_repository_base())
    assert not base.action_only


def test_action_validation_base():
    base = ActionValidationBase(dummy_repository_base())
    assert base.action_only
