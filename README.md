ably-python
-----------

.. image:: https://img.shields.io/travis/ably/ably-python.svg
        :target: https://travis-ci.org/ably/ably-python

.. image:: https://img.shields.io/pypi/v/ably-python.svg
        :target: https://pypi.python.org/pypi/ably-python


Python REST client for Ably real-time messaging service

## Dependencies

The ably-python client has one dependency, 
[requests>=1.0.0](https://github.com/kennethreitz/requests)

## Features

- Connection Pooling
- HTTP Keep-Alive
- Python 2.6-3.3
- Compatible with gevent

## Installation

### From PyPi

    pip install ably-python

### From a git url

    pip install -e git+https://github.com/ably/ably-python#egg=AblyPython

### Locally

    git clone https://github.com/ably/ably-python.git
    cd ably-python
    python setup.py install

#### To run the tests

    python setup.py test

## Basic Usage

```python
from ably.rest import AblyRest

ably = AblyRest("key_str")
ably.time() # returns the server time in ms since the unix epoch
ably.stats() # returns an array of stats

# Channels:
# Publish a message to channel 'foo'
ably.channels.foo.publish('msg_name', 'msg_data')

# Get the history for channel 'foo'
ably.channels.foo.history()

# Get presence for channel 'foo'
ably.channels.foo.presence()
```
## Options

### Credentials

You can provide either a `key` string or `app_id` + `key_id` + `key_value`
combination.

```python
ably = AblyRest("key-string")
```
or

```python
ably = AblyRest(app_id="app-id", key_id="key-id", key_value="key-value")
```
