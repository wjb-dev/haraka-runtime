# setup.py
from setuptools import setup, find_packages

setup(
    name="haraka-runtime",
    version="0.1.0",
    description="Haraka Runtime SDK for building adapters and orchestrating services",
    package_dir={"": "src"},
    packages=find_packages(
        where="src", exclude=["tests", "docs", "examples", ".github"]
    ),
    install_requires=[
        "PyYAML",  # for manifest_loader
        # add other runtime deps here
    ],
    python_requires=">=3.8",
)
