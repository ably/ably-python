from setuptools import setup

with open('LONG_DESCRIPTION.rst') as f:
    long_description = f.read()

setup(
    name='ably',
    version='1.1.1',
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['ably', 'ably.http', 'ably.rest', 'ably.transport',
              'ably.types', 'ably.util'],
    install_requires=['methoddispatch>=3.0.2,<4',
                      'msgpack>=1.0.0,<2',
                      'requests>=2.7.0,<3'],
    extras_require={
        'oldcrypto': ['pycrypto>=2.6.1'],
        'crypto': ['pycryptodome'],
    },
    author="Ably",
    author_email='support@ably.io',
    url='https://github.com/ably/ably-python',
    description="A Python client library for ably.io realtime messaging",
    long_description=long_description,
)
