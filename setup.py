#!/usr/bin/env python3
"""Setup script for TuxSec Agent."""

from setuptools import setup, find_packages
import os

# Read version from __init__.py
version = {}
with open("agent/__init__.py") as f:
    for line in f:
        if line.startswith("__version__"):
            exec(line, version)
            break

# Read README
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="tuxsec-agent",
    version=version.get("__version__", "2.0.0"),
    author="MrMEEE",
    author_email="you@example.com",
    description="TuxSec Agent - Secure Linux System Management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/MrMEEE/tuxsec",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Systems Administration",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PyYAML>=6.0",
        "httpx>=0.24",
        "aiohttp>=3.8",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21",
            "black>=23.0",
            "flake8>=6.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "tuxsec-rootd=agent.rootd.daemon:main",
            "tuxsec-agent=agent.userspace.agent:main",
            "tuxsec-cli=agent.userspace.cli:main",
            "tuxsec-setup=agent.userspace.setup:main",
        ],
    },
    include_package_data=True,
    package_data={
        "agent": [
            "systemd/*.service",
            "selinux/*.te",
            "selinux/*.fc",
            "selinux/*.if",
            "*.yaml.example",
        ],
    },
)
