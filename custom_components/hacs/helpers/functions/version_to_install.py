"""Install helper for repositories."""


def version_to_install(repository):
    """Determine which version to isntall."""
    if repository.data.last_version is not None:
        if repository.data.selected_tag is not None:
            if repository.data.selected_tag == repository.data.last_version:
                repository.data.selected_tag = None
                return repository.data.last_version
            return repository.data.selected_tag
        return repository.data.last_version
    if repository.data.selected_tag is not None:
        if repository.data.selected_tag == repository.data.default_branch:
            return repository.data.default_branch
        if repository.data.selected_tag in repository.data.published_tags:
            return repository.data.selected_tag
    if repository.data.default_branch is None:
        return "main"
    return repository.data.default_branch
