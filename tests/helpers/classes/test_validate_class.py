from custom_components.hacs.utils.validate import Validate


def test_validate():
    validate = Validate()
    assert validate.success
    validate.errors.append("test")
    assert not validate.success
