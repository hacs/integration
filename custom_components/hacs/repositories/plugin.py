"""Class for plugins in HACS."""
import json
from aiogithubapi import AIOGitHubException
from .repository import HacsRepository, register_repository_class


@register_repository_class
class HacsPlugin(HacsRepository):
    """Plugins in HACS."""

    category = "plugin"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category
        self.information.file_name = None
        self.information.javascript_type = None
        self.content.path.local = (
            f"{self.system.config_path}/www/community/{full_name.split('/')[-1]}"
        )

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        await self.get_plugin_location()

        if self.content.path.remote is None:
            self.validate.errors.append("Repostitory structure not compliant")

        if self.content.path.remote == "release":
            self.content.single = True

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.system.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def registration(self):
        """Registration."""
        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

    async def update_repository(self):
        """Update."""
        if self.github.ratelimits.remaining == 0:
            return
        # Run common update steps.
        await self.common_update()

        # Get plugin objects.
        await self.get_plugin_location()

        # Get JS type
        await self.parse_readme_for_jstype()

        if self.content.path.remote is None:
            self.validate.errors.append("Repostitory structure not compliant")

        if self.content.path.remote == "release":
            self.content.single = True

        self.content.files = []
        for filename in self.content.objects:
            self.content.files.append(filename.name)

    async def get_plugin_location(self):
        """Get plugin location."""
        if self.content.path.remote is not None:
            return

        possible_locations = ["dist", "release", ""]

        if self.repository_manifest:
            if self.repository_manifest.content_in_root:
                possible_locations = [""]

        for location in possible_locations:
            if self.content.path.remote is not None:
                continue
            try:
                objects = []
                files = []
                if location != "release":
                    try:
                        objects = await self.repository_object.get_contents(
                            location, self.ref
                        )
                    except AIOGitHubException:
                        continue
                else:
                    await self.get_releases()
                    if self.releases.releases:
                        if self.releases.last_release_object.assets is not None:
                            objects = self.releases.last_release_object.assets

                for item in objects:
                    if item.name.endswith(".js"):
                        files.append(item.name)

                # Handler for plug requirement 3
                valid_filenames = [
                    f"{self.information.name.replace('lovelace-', '')}.js",
                    f"{self.information.name}.js",
                    f"{self.information.name}.umd.js",
                    f"{self.information.name}-bundle.js",
                ]

                if self.repository_manifest:
                    if self.repository_manifest.filename:
                        valid_filenames.append(self.repository_manifest.filename)

                for name in valid_filenames:
                    if name in files:
                        # YES! We got it!
                        self.information.file_name = name
                        self.content.path.remote = location
                        self.content.objects = objects
                        self.content.files = files
                        break

            except SystemError:
                pass

    async def get_package_content(self):
        """Get package content."""
        try:
            package = await self.repository_object.get_contents("package.json")
            package = json.loads(package.content)

            if package:
                self.information.authors = package["author"]
        except Exception:  # pylint: disable=broad-except
            pass

    async def parse_readme_for_jstype(self):
        """Parse the readme looking for js type."""
        readme = None
        readme_files = ["readme", "readme.md"]
        root = await self.repository_object.get_contents("")
        for file in root:
            if file.name.lower() in readme_files:
                readme = await self.repository_object.get_contents(file.name)
                break

        if readme is None:
            return

        readme = readme.content
        for line in readme.splitlines():
            if "type: module" in line:
                self.information.javascript_type = "module"
                break
            elif "type: js" in line:
                self.information.javascript_type = "js"
                break
