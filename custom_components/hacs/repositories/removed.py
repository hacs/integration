"""Object for removed repositories."""
import attr


@attr.s(auto_attribs=True)
class RemovedRepository:
    repository: str = ""
    reason: str = ""
    link: str = ""
    removal_type: str = ""  # archived, not_compliant, critical, dev, broken
    acknowledged: bool = False
