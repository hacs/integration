import json

from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent

from custom_components.hacs.validate.wake_word_model import Validator


def _tree(*paths):
    """Build a repository tree from a list of file paths."""
    return [
        AIOGitHubAPIRepositoryTreeContent({"path": path, "type": "blob"}, "test/test", "main")
        for path in paths
    ]


def _valid_config(model="my_wake_word.tflite"):
    return {
        "type": "micro",
        "wake_word": "My Wake Word",
        "model": model,
    }


def _set_documentation(repository, content):
    """Make get_documentation return the given content."""

    async def _get_documentation(**__):
        return content

    repository.get_documentation = _get_documentation


async def test_valid_wake_word_repository(repository_wake_word):
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert not check.failed


async def test_nested_wake_word_files_rejected(repository_wake_word):
    """Wake word files in a subdirectory of the content dir are rejected."""
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
        "custom_wake_words/extra/second.json",
        "custom_wake_words/extra/second.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_valid_wake_word_repository_content_in_root(repository_wake_word):
    """hacs.json in the root must not be mistaken for the wake word config."""
    repository_wake_word.repository_manifest.content_in_root = True
    repository_wake_word.tree = _tree(
        "hacs.json",
        "my_wake_word.json",
        "my_wake_word.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert not check.failed


async def test_no_config_file(repository_wake_word):
    repository_wake_word.tree = _tree("custom_wake_words/my_wake_word.tflite")

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_multiple_config_files(repository_wake_word):
    repository_wake_word.tree = _tree(
        "custom_wake_words/one.json",
        "custom_wake_words/one.tflite",
        "custom_wake_words/two.json",
        "custom_wake_words/two.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_invalid_json(repository_wake_word):
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
    )
    _set_documentation(repository_wake_word, "{not valid json")

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_missing_required_key(repository_wake_word):
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
    )
    config = _valid_config()
    del config["wake_word"]
    _set_documentation(repository_wake_word, json.dumps(config))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_model_name_mismatch(repository_wake_word):
    """config["model"] must match the config file stem."""
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config(model="other.tflite")))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_missing_model_file(repository_wake_word):
    """The model referenced by the config must exist in the directory."""
    repository_wake_word.tree = _tree("custom_wake_words/my_wake_word.json")
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_multiple_model_files(repository_wake_word):
    """A repository must ship exactly one model file."""
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/my_wake_word.tflite",
        "custom_wake_words/extra.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config()))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed


async def test_config_and_model_stem_mismatch(repository_wake_word):
    """The config file and model file must share the same stem."""
    repository_wake_word.tree = _tree(
        "custom_wake_words/my_wake_word.json",
        "custom_wake_words/other.tflite",
    )
    _set_documentation(repository_wake_word, json.dumps(_valid_config(model="other.tflite")))

    check = Validator(repository_wake_word)
    await check.execute_validation()
    assert check.failed
