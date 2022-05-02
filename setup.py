from setuptools import setup, find_packages


setup(
    name="captol",
    version="2.2",
    license="MIT",
    description="A python-based GUI application for reconstructing screen-sharing documents.",
    packages=find_packages(),
    package_data={"": ["*.ico"]}
)
