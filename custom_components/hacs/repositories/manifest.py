"""Manifest handling of a repository."""


class HacsManifest:
    """HacsManifest class."""

    def __init__(self, manifest):
        """Initialize."""
        self.manifest = manifest

    @property
    def name(self):
        """Return the name."""
        return self.manifest.get("name")

    @property
    def content_in_root(self):
        """Return a bool to indicate that the content is in the roop of the repository."""
        return self.manifest.get("content_in_root")

    @property
    def filename(self):
        """Return the filename."""
        return self.manifest.get("filename")

    @property
    def domains(self):
        """Return the domains."""
        if isinstance(self.manifest.get("domains", []), str):
            return [self.manifest.get("domains", [])]
        return self.manifest.get("domains", [])

    @property
    def country(self):
        """Return the country."""
        if isinstance(self.manifest.get("country", []), str):
            return [self.manifest.get("country", [])]
        return self.manifest.get("country", [])

    @property
    def homeassistant(self):
        """Return the minimum homeassistant version."""
        return self.manifest.get("homeassistant")

    @property
    def persistent_directory(self):
        """Return the persistent_directory."""
        return self.manifest.get("persistent_directory")

    @property
    def iot_class(self):
        """Return the iot_class."""
        return self.manifest.get("iot_class")

    @property
    def render_readme(self):
        """Return a bool to indicate that the readme file should be rendered."""
        return self.manifest.get("render_readme")
