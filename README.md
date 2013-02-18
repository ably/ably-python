ably-python
-----------

Ably.io python client library

## Dependencies

The ably-python client has one dependency, 
[requests>=1.0.0](https://github.com/kennethreitz/requests)

## Installation

### From PyPi

    pip install ably-python

### From a git url

    pip install git@bitbucket.org:jjwchoy/ably-python.git

### Locally

    git clone git@bitbucket.org:jjwchoy/ably-python.git
    cd ably-python
    python setup.py install

## Usage

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

## Features

- Connection Pooling
- HTTP Keep Alive


