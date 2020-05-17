# pylint: disable=invalid-name, missing-docstring
hacs = []
removed_repositories = []
rules = {}


def get_hacs():
    if not hacs:
        from custom_components.hacs.hacsbase import Hacs

        hacs.append(Hacs())

    return hacs[0]


def is_removed(repository):
    return repository in [x.repository for x in removed_repositories]


def get_removed(repository):
    if not is_removed(repository):
        from custom_components.hacs.repositories.removed import RemovedRepository

        removed_repo = RemovedRepository()
        removed_repo.repository = repository
        removed_repositories.append(removed_repo)
    filter_repos = [
        x for x in removed_repositories if x.repository.lower() == repository.lower()
    ]
    return filter_repos[0]
