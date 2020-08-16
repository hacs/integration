from custom_components.hacs.validate.base import ActionValidationBase, ValidationBase


def test_validation_base(repository):
    base = ValidationBase(repository)
    assert not base.action_only


def test_action_validation_base(repository):
    base = ActionValidationBase(repository)
    assert base.action_only
