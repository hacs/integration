"""HACS/util/modules."""
from pathlib import Path
from functools import lru_cache


@lru_cache(maxsize=None)
def get_modules(manager_path: str, folder: str = "entries") -> list[str]:
    """Retrun a list of modules inside a directory"""
    ignore_files = ("base.py", "__init__.py", "manager.py")
    module_files = Path(manager_path).parent.joinpath(folder)

    return [
        module.stem
        for module in module_files.glob("*.py")
        if module.name not in ignore_files
    ]
