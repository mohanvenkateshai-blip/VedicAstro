"""vedic-knowledge — shared Vedic knowledge graph package."""

from pathlib import Path

from setuptools import find_packages, setup

README = (Path(__file__).parent / "README.md").read_text(encoding="utf-8")

setup(
    name="vedic-knowledge",
    version="0.1.0",
    description="Shared GraphRAG + knowledge integration for VedicAstro and panchanga_muhurtha",
    long_description=README,
    long_description_content_type="text/markdown",
    author="VedicAstro / MuhurtaCosmos",
    python_requires=">=3.10",
    packages=find_packages(exclude=("tests", "tests.*")),
    include_package_data=True,
    package_data={
        "vedic_knowledge.graph": ["graph.json"],
    },
    install_requires=[
        # Core graph needs only stdlib. Optional extras below.
    ],
    extras_require={
        "embed": ["numpy>=1.24", "fastembed>=0.3"],
        "full": ["numpy>=1.24", "fastembed>=0.3"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
)
