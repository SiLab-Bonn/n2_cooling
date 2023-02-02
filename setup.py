#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

import n2_cooling

author = 'Christian Bespin, Toko Hirono'
author_email = ''
version = '0.1.0'

# Requirements for core functionality from requirements.txt
with open('requirements.txt') as f:
    install_requires = f.read().splitlines()

setup(
    name='n2cooling',
    version=version,
    description='Control software for N2 cooling system',
    url='https://github.com/SiLab-Bonn/n2_cooling',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    python_requires=">=3.7",
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
)
