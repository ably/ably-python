from setuptools import setup

with open('LONG_DESCRIPTION.rst') as f:
    long_description = f.read()

setup(
    name='ably',
    version='1.0.0',
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['ably', 'ably.http', 'ably.rest', 'ably.transport',
              'ably.types', 'ably.util'],
    install_requires=['msgpack-python>=0.4.6',
                      'pycrypto>=2.6.1',
                      'requests>=2.7.0,<2.8',
                      'six>=1.9.0'],  # remember to update these
                                      # according to requirements.txt!
                                      # there's no easy way to reuse this.
    author="Ably",
    author_email='support@ably.io',
    url='https://github.com/ably/ably-python',
    description="A Python client library for ably.io realtime messaging",
    long_description=long_description,
)
