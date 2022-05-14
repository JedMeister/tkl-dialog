#!/usr/bin/python3

from distutils.core import setup

setup(
    name="tkl-duialog",
    version="0.1",
    author="Jeremy Davis",
    author_email="jeremy@turnkeylinux.org",
    url="https://github.com/turnkeylinux/tkl-dialog",
    packages=["tkl_dialog"],
    package_data={"tkl_dialog": ["py.typed"]}
)
