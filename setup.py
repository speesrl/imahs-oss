from setuptools import setup, find_packages

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("README.md") as f:
    long_description = f.read()

with open("LICENSE") as f:
    license = f.read()

setup(
    name="mop",
    version="1.0",
    author="Aly Shmahell",
    description="an Event-Driven Reactive Architecture (EDA) with an Actor/Reactor Model for Scalable Context Exchange in Large Model Applications.",
    long_description=long_description,
    license=license,
    packages=find_packages(),
    install_requires=requirements,
)
