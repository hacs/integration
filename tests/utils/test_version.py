from custom_components.hacs.utils import version


def test_version_to_download(repository):
    repository.data.selected_tag = "main"
    assert repository.version_to_download() == "main"

    repository.data.default_branch = None
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "2"
    assert repository.version_to_download() == "2"

    repository.data.selected_tag = None
    repository.data.last_version = "3"
    assert repository.version_to_download() == "3"

    repository.data.selected_tag = None
    repository.data.last_version = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "2"
    repository.data.last_version = None
    assert repository.version_to_download() == "2"

    repository.data.selected_tag = "main"
    repository.data.last_version = None
    assert repository.version_to_download() == "main"

    repository.data.selected_tag = "3"
    repository.data.last_version = "3"
    repository.version_to_download()
    assert repository.data.selected_tag is None

    repository.data.default_branch = "dev"
    repository.data.last_version = None
    repository.data.selected_tag = None
    assert repository.version_to_download() == "dev"

    repository.data.default_branch = "main"
    repository.data.last_version = "2"
    assert repository.version_to_download() == "2"

    repository.data.default_branch = "main"
    repository.data.selected_tag = "main"
    repository.data.last_version = None
    assert repository.version_to_download() == "main"

    assert version.version_left_higher_then_right("1", None) is None
