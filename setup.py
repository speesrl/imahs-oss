# my_module/setup.py
from setuptools import setup, find_packages


with open("requirements.txt") as f:
    requirements = f.read().splitlines()
setup(
    name="mop",
    version="0.0.1",
    author="Aly Shmahell",
    packages=find_packages(),
    install_requires=requirements,
)
