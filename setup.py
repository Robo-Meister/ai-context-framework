from __future__ import annotations

from pathlib import Path

from setuptools import find_packages, setup


BASE_DIR = Path(__file__).parent.resolve()
README_PATH = BASE_DIR / "README.md"
DOCS_DIR = BASE_DIR / "docs"

if DOCS_DIR.exists():
    doc_files = [
        str(path.relative_to(BASE_DIR))
        for path in DOCS_DIR.rglob("*")
        if path.is_file()
    ]
else:
    doc_files = []

setup(
    name="caiengine",
    version="0.2.1",
    packages=find_packages(where="src", include=["caiengine", "caiengine.*", "sitecustomize"]),
    package_dir={"": "src"},
    include_package_data=True,
    data_files=[("share/caiengine/docs", doc_files)] if doc_files else [],
    install_requires=[
        "numpy>=2.2.6",
        "sympy>=1.14.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.30.0",
        "httpx>=0.27.0",
    ],
    extras_require={
        "ai": [
            "torch>=2.3.1",
            "onnx>=1.17.0",
            "PyYAML>=6.0.2",
        ],
        "redis": ["redis>=6.1.0"],
        "kafka": ["kafka-python>=2.0.2"],
        "mysql": ["mysql-connector-python>=9.1.0"],
        "postgresql": ["psycopg2-binary>=2.9.10"],
        "storage": [
            "mysql-connector-python>=9.1.0",
            "psycopg2-binary>=2.9.10",
        ],
        "docs": ["mkdocs>=1.6.0"],
        "dev": [
            "pytest>=8.3.5",
            "pytest-cov>=4.1.0",
            "mypy",
            "black",
        ],
    },
    author="Paweł Nowak",
    author_email="pawel.nowak@robo-meister.com",
    description="A Context-Aware AI Engine for decision automation, workflow reasoning, and dynamic task orchestration",
    long_description=README_PATH.read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Robo-Meister/ai-context-framework",
    project_urls={
        "Homepage": "https://github.com/Robo-Meister/ai-context-framework",
        "Repository": "https://github.com/Robo-Meister/ai-context-framework",
    },
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    entry_points={
        "console_scripts": [
            "context=caiengine.cli:main",
        ]
    },
    python_requires=">=3.6",
)
