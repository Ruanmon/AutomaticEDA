"""Package setup for AutomaticEDA."""

from setuptools import find_packages, setup

setup(
    name="automatic-eda",
    version="0.1.0",
    description=(
        "An LLM-powered agent EDA tool for digital IC design that generates "
        "SystemVerilog RTL, testbenches, and SVA from plain-text specifications."
    ),
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "eda-agent=main:main",
        ],
    },
)
