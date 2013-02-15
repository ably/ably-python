from setuptools import setup

setup(
    name='ably-python',
    version='0.1dev',
    packages=['ably',],
    install_requires=['requests>=1.0.0',],
    long_description=open('README.md').read(),
    test_suite='test.ably.restsuite'
)

