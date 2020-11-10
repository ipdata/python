import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
# ToDo: add bumpversion, run in ci
setup(
    name="ipdata",
    version="3.4.2",
    description="Python Client for the ipdata IP Geolocation API",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/ipdata/python",
    author="Jonathan Kosgei",
    author_email="jonatha@ipdata.co",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
    ],
    packages=["ipdata"],
    include_package_data=True,
    install_requires=["requests", "ipaddress", "click"],
    entry_points={
        'console_scripts': [
            'ipdata = ipdata.cli:todo',
        ]
    },
)
