from setuptools import setup, find_packages

setup(
    name="my_package",           # Package name (unique on PyPI)
    version="0.1.0",             # Version number
    packages=find_packages(),    # Automatically find packages
    install_requires=[           # List dependencies here
        # "requests>=2.20.0",
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A short description of my package",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/my_package",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)
