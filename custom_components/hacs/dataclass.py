from dataclasses import dataclass


@dataclass
class RepositoryInterface:
    full_name: str

    @property
    def owner(self):
        return self.full_name.split("/")[0]

    @property
    def repository(self):
        return self.full_name.split("/")[1]

    def __repr__(self) -> str:
        return self.full_name

    def __str__(self) -> str:
        return self.full_name
