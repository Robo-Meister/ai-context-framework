from setuptools import setup, find_packages

setup(
    name="caiengine",  # your package name, must be unique on PyPI
    version="0.1.0",
    packages=find_packages(),

    install_requires=[
        "numpy>=2.2.6",
        "torch>=2.7.0",
        "sympy>=1.14.0",
    ],
    extras_require={
        "redis": ["redis>=6.1.0"],
        "kafka": ["kafka-python>=2.0.2"],
        "dev": [
            "pytest>=8.3.5",
            "mypy",
            "black"
        ],  # optional dev deps
    },
    author="Paweł Nowak",
    author_email="pawel.nowak@robo-meister.com",
    description="A Context-Aware AI Engine for decision automation, workflow reasoning, and dynamic task orchestration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Robo-Meister/ai-context-framework.git",

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Artificial Intelligence",
    ],

    entry_points={
        "console_scripts": [
            "context=ai_context.cli:main",
        ]
    },

    python_requires='>=3.6',
    include_package_data=True,  # to include files from MANIFEST.in if needed
)
