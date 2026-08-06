"""Packaging for android-ai-agent.

The agent can be used directly from a clone (``python agent.py ...``) or
installed via ``pip install -e .`` to get the ``android-agent`` console command.
"""

from setuptools import find_packages, setup

setup(
    name="android-ai-agent",
    version="0.2.0",
    description="Natural-language task execution on Android — a privacy-first AI agent.",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="axe git",
    author_email="axe01010@users.noreply.github.com",
    url="https://github.com/axe01010/android-ai-agent",
    license="MIT",
    packages=find_packages(include=["plugins*"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=["PyYAML>=6.0"],
    entry_points={"console_scripts": ["agent=agent:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
)