from setuptools import setup

setup(
    name='ably-python',
    version='0.1dev',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
    ],
    packages=['ably',],
    install_requires=['requests>=1.0.0',],
    long_description='',
    test_suite='nose.collector',
    tests_require=['nose>=1.0.0',]
)

