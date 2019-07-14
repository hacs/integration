"""RepositoryInformationView, used for the frontend."""
# pylint: disable=missing-docstring
from distutils.version import LooseVersion
from homeassistant.const import __version__ as HAVERSION
from .repositoryinformation import RepositoryInformation

class RepositoryInformationView(RepositoryInformation):

    @property
    def additional_info(self):
        if self.repository.additional_info is not None:
            return self.repository.additional_info
        return ""

    @property
    def main_action(self):
        actions = {
            "default": "INSTALL",
            "installed": "REINSTALL",
            "pending-restart": "REINSTALL",
            "pending-update": "UPGRADE"
        }
        return actions[self.status]


    @property
    def display_authors(self):
        if self.repository.authors:
            if self.repository.repository_type == "integration":
                authors = "<p>Author(s): "
                for author in self.repository.authors:
                    if "@" in author:
                        author = author.split("@")[-1]
                    authors += "<a rel='noreferrer' href='https://github.com/{author}' target='_blank' style='color: var(--primary-color) !important; margin: 2'> @{author}</a>".format(
                        author=author
                    )
                authors += "</p>"
            else:
                authors = "<p>Author: {}</p>".format(self.repository.authors)
        else:
            authors = ""
        return authors

    @property
    def local_path(self):
        return self.repository.local_path

    @property
    def javascript_type(self):
        return self.repository.javascript_type

    @property
    def show_beta(self):
        return self.repository.show_beta

    @property
    def full_name(self):
        return self.repository_name.split("/")[-1]
