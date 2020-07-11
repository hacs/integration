"""Setup configuration."""
import setuptools

setuptools.setup(
    name="custom_components",
    version="0",
    packages=setuptools.find_packages(exclude=["tests", "tests.*"]),
)
