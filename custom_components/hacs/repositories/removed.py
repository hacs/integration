"""Object for removed repositories."""
import attr


@attr.s(auto_attribs=True)
class RemovedRepository:
    repository: str = None
    reason: str = None
    link: str = None
    removal_type: str = None  # archived, not_compliant, critical, dev
    acknowledged: bool = False
