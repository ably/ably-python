#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


with open('README.txt') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read().replace('.. :changelog:', '')

requirements = [
    'msgpack-python==0.4.6',
    'pycrypto==2.6.1',
    'requests==2.6.0',
    'six==1.9.0',
]

test_requirements = [
    'nose==1.3.6',
    'responses==0.3.0',
    'mock==1.0.1',
]

setup(
    name='ably-python',
    version='0.1.0',
    description="Python REST client for Ably real-time messaging service",
    long_description=readme + '\n\n' + history,
    # author="",
    # author_email='',
    # license="",
    url='https://github.com/ably/ably-python',
    packages=[
        'ably',
    ],
    package_dir={'ably': 'ably'},
    include_package_data=True,
    install_requires=requirements,
    zip_safe=False,
    keywords='ably',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        # 'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    test_suite='nose.collector',
    tests_require=test_requirements
)
