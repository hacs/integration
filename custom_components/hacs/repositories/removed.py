"""Object for removed repositories."""
import attr


@attr.s(auto_attribs=True)
class RemovedRepository:
    repository: str = None
    reason: str = None
    link: str = None
    removal_type: str = None  # archived, not_compliant, critical, dev, broken
    acknowledged: bool = False

    def update_data(self, data: dict):
        """Update data of the repository."""
        for key in data:
            if key in self.__dict__:
                setattr(self, key, data[key])
