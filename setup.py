#!/usr/bin/env python2

from distutils.core import setup

setup(
    name='gitto',
    version='0.0.1',

    url='',
    description="Poor man's git hosting",

    classifiers = [
        "Development Status :: 3 - Alpha",
        "Environment :: No Input/Output (Daemon)",
        "Framework :: Twisted",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: Software Development"
    ],

    author='bhuztez',
    author_email='bhuztez@gmail.com',

    requires=['Twisted (>= 11.0)'],

    packages = ['gitto', 'twisted.plugins'],
    zip_safe = False,
)
