#!/usr/bin/env python3
from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="maxim",
    version="1.0.0",
    description="Penetration Testing Command Center for Kali Linux",
    long_description=Path("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    author="stoev",
    url="https://github.com/stoev/maxim",
    packages=find_packages(),
    include_package_data=True,
    package_data={"maxim": ["VERSION"]},
    python_requires=">=3.10",
    install_requires=[
        "PyQt5>=5.15",
    ],
    entry_points={
        "console_scripts": [
            "maxim=maxim.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Security",
        "Environment :: X11 Applications :: Qt",
    ],
)
