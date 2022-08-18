from setuptools import setup

with open('LONG_DESCRIPTION.rst') as f:
    long_description = f.read()

setup(
    name='ably',
    version='1.2.1',
    classifiers=[
        'Development Status :: 6 - Mature',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    packages=['ably', 'ably.http', 'ably.rest', 'ably.transport',
              'ably.types', 'ably.util'],
    install_requires=['methoddispatch>=3.0.2,<4',
                      'msgpack>=1.0.0,<2',
                      'httpx>=0.20.0,<1',
                      'h2>=4.0.0,<5'],
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
