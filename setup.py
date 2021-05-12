#!/usr/bin/env python

from setuptools import setup
from setuptools import find_packages

import n2_cooling

author = 'Christian Bespin, Toko Hirono'
author_email = ''

# Requirements
install_requires = ['basil-daq', 'numpy', 'online_monitor', 'simple-pid', 'tables', 'pyzmq']

setup(
    name='n2cooling',
    version=n2_cooling.version,
    description='Control software for N2 cooling system',
    url='https://github.com/SiLab-Bonn/n2_cooling',
    license='',
    long_description='',
    author=author,
    maintainer=author,
    author_email=author_email,
    maintainer_email=author_email,
    install_requires=install_requires,
    python_requires=">=3.0",
    packages=find_packages(),
    include_package_data=True,
    platforms='any',
)
