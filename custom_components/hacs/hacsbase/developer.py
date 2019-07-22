"""Developer settings/tools."""


class Developer:
    """Developer settings/tools."""

    template_id = "Repository ID"
    template_content = ""
    template_raw = ""

    @property
    def devcontainer(self):
        """Is it a devcontainer?"""
        import os

        if "DEVCONTAINER" in os.environ:
            return True
        return False
