"""Checks to run as an action."""
import os
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.helpers.information import get_tree

BRANDS_REPO = "https://github.com/home-assistant/brands"
WHEEL_REPO = "https://github.com/home-assistant/wheels-custom-integrations"


async def run_action_checks(repository):
    """Checks to run as an action."""
    issues = []
    if os.getenv("SKIP_BRANDS_CHECK") is None:
        brands = await repository.hacs.github.get_repo("home-assistant/brands")
        brandstree = await get_tree(brands, "master")
        if repository.integration_manifest["domain"] not in [
            x.filename for x in brandstree
        ]:
            issues.append(f"Integration not added to {BRANDS_REPO}")
        else:
            repository.logger.info(f"Integration is added to {BRANDS_REPO}, nice!")

    if (
        repository.integration_manifest.get("requirements") is not None
        and len(repository.integration_manifest.get("requirements")) != 0
    ):
        wheels = await repository.hacs.github.get_repo(
            "home-assistant/wheels-custom-integrations"
        )
        wheeltree = await get_tree(wheels, "master")
        wheelfiles = [x.filename for x in wheeltree]
        if (
            f"{repository.integration_manifest['domain']}.json" in wheelfiles
            or repository.integration_manifest["domain"] in wheelfiles
        ):
            repository.logger.info(f"Integration is added to {WHEEL_REPO}, nice!")
        else:
            issues.append(f"Integration not added to {WHEEL_REPO}")

    if issues:
        for issue in issues:
            repository.logger.error(issue)
        raise HacsException(f"Found issues while validating the repository")
