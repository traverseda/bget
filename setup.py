#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = ['Click>=6.0',
                'PyXdg',
                'click-config-file',
                'selenium',
                'warcprox',
                ]

setup_requirements = [ ]

test_requirements = [ ]

setup(
    author="Alex Davies",
    author_email='traverse.da@gmail.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="Download websites using a real web browser",
    entry_points={
        'console_scripts': [
            'bget=bget.cli:main',
        ],
    },
    install_requires=requirements,
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='bget',
    name='bget',
    packages=find_packages(include=['bget']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/traverseda/bget',
    version='0.1.0',
    zip_safe=False,
)
