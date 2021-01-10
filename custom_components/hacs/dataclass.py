from dataclasses import dataclass


@dataclass
class RepositoryIdentifier:
    full_name: str

    @property
    def owner(self):
        return self.full_name.split("/")[0]

    @property
    def repository(self):
        return self.full_name.split("/")[1]

    def __repr__(self) -> str:
        return self.full_name.lower()

    def __str__(self) -> str:
        return self.full_name.lower()
