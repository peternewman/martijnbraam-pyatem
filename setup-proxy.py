# Copyright 2022 - 2022, Martijn Braam and the OpenAtem contributors
# SPDX-License-Identifier: LGPL-3.0-only
from setuptools import setup

setup(
    name='openswitcher-proxy',
    version='0.12.3',
    packages=['openswitcher_proxy'],
    url='https://git.sr.ht/~martijnbraam/pyatem',
    license='LGPL3',
    author='Martijn Braam',
    author_email='martijn@brixit.nl',
    description='Proxy for ATEM switchers',
    requires=['pyatem', 'toml'],
    extras_require={
        'midi': ['python-rtmidi'],
        'mqtt': ['paho-mqtt'],
    },
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Operating System :: POSIX :: Linux',
    ],
    entry_points={
        'console_scripts': ['openswitcher-proxy=openswitcher_proxy.__main__:main'],
    },
)
