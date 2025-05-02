from setuptools import find_packages, setup


with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="openmanus",
    version="0.1.0",
    author="mannaandpoem and OpenManus Team",
    author_email="mannaandpoem@gmail.com",
    description="A versatile agent that can solve various tasks using multiple tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mannaandpoem/OpenManus",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.1.0",
        "openai>=1.58.1",
        "tenacity>=8.0.0",
        "pyyaml>=6.0.0",
        "loguru>=0.7.0",
        "numpy",
        "pillow>=10.0.0",
        "colorama>=0.4.6",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    entry_points={
        "console_scripts": [
            "openmanus=main:main",
        ],
    },
)
