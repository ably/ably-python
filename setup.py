from setuptools import setup

setup(
    name='ably',
    version='0.1.dev',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    packages=['ably', 'ably.http', 'ably.rest', 'ably.transport', 'ably.types', 'ably.util'],
    install_requires=['msgpack-python>=0.4.6',
                      'pycrypto>=2.6.1',
                      'requests>=2.7.0,<2.8',
                      'six>=1.9.0'],  # remember to update these on tox.ini!
                                      # there's no easy way to reuse this.
    long_description='',
)
