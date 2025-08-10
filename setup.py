from setuptools import setup, find_packages
from setuptools import setup, find_packages

setup(
    name="social-content-engine",
    version="0.1.0",
    description="A modular backend system for automating content creation for social media platforms",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/social_content_engine",
    packages=find_packages(
        where="src"
    ),  # This will find all sub-packages, including config
    package_dir={"": "src"},
    include_package_data=True,
    install_requires=[
        "flask",
        "gtts",
        "moviepy",
        "openai",
        "PyPDF2",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
