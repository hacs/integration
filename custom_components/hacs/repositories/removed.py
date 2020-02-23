"""Object for removed repositories."""
import attr


@attr.s(auto_attribs=True)
class RemovedRepository:
    repository: str = ""
    reason: str = ""
    link: str = ""
    removal_type: str = ""  # archived, not_compliant, critical, dev
    acknowledged: bool = False

    def update_data(self, data: dict):
        """Update data of the repository."""
        for key in data:
            if key in self.__dict__:
                setattr(self, key, data[key])
