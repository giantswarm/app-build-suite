import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="app_build_suite",
    version="v1.4.3",
    author="Łukasz Piątkowski",
    author_email="lukasz@giantswarm.io",
    description="An app build suite for GiantSwarm app platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/giantswarm/app-build-suite",
    packages=setuptools.find_packages(),
    keywords=["helm chart", "building"],
    classifiers=[
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
    python_requires=">=3.12",
)
