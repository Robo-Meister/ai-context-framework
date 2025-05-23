from setuptools import setup, find_packages

setup(
    name="cotext-ai",  # your package name, must be unique on PyPI
    version="0.1.0",  # initial version
    packages=find_packages(),  # auto-detect packages

    install_requires=[
        "numpy>=1.20.0",
    ],
    extras_require={
        "redis": ["redis>=4.0.0"],
        "dev": ["pytest", "mypy", "black"],  # optional dev deps
    },
    author="Paweł Nowak",
    author_email="pawel.nowak@robo-meister.com",
    description="Contextual AI module for intelligent message understanding, role-based context mapping, and semantic processing.",
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

    python_requires='>=3.6',
    include_package_data=True,  # to include files from MANIFEST.in if needed
)
