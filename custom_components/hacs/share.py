import os

SHARE = {"hacs": None, "factory": None, "removed_repositories": [], "rules": {}}


def get_hacs():
    if SHARE["hacs"] is None:
        from custom_components.hacs.hacsbase.hacs import Hacs

        _hacs = Hacs()

        if not os.getenv("PYTEST") and os.getenv("GITHUB_ACTION"):
            _hacs.action = True

        SHARE["hacs"] = _hacs

    return SHARE["hacs"]


def get_factory():
    if SHARE["factory"] is None:
        from custom_components.hacs.operational.task_factory import HacsTaskFactory

        SHARE["factory"] = HacsTaskFactory()

    return SHARE["factory"]


def is_removed(repository):
    return repository in [x.repository for x in SHARE["removed_repositories"]]


def get_removed(repository):
    if not is_removed(repository):
        from custom_components.hacs.repositories.removed import RemovedRepository

        removed_repo = RemovedRepository()
        removed_repo.repository = repository
        SHARE["removed_repositories"].append(removed_repo)
    filter_repos = [
        x
        for x in SHARE["removed_repositories"]
        if x.repository.lower() == repository.lower()
    ]
    if filter_repos:
        return filter_repos.pop()
    return None


def list_removed_repositories():
    return SHARE["removed_repositories"]
