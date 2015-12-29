ably-python
-----------

[![Build Status](https://travis-ci.org/ably/ably-python.svg?branch=master)](https://travis-ci.org/ably/ably-python)
[![Coverage Status](https://coveralls.io/repos/ably/ably-python/badge.svg?branch=master&service=github)](https://coveralls.io/github/ably/ably-python?branch=master)

Ably.io Python client library - REST interface. Supports Python 2.7-3.5.

## Documentation

Visit https://www.ably.io/documentation for a complete API reference and more examples.

## Installation

### From PyPi (soon)

    pip install ably-python

### From a git url

    pip install -e git+https://github.com/ably/ably-python#egg=AblyPython

### Locally

    git clone https://github.com/ably/ably-python.git
    cd ably-python
    python setup.py install

#### To run the tests

    git submodule init
    git submodule update
    pip install -r requirements-test.txt
    nosetests

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

You can provide either a `key`, a `token` or, attributes to the `Options` object.

```python
ably = AblyRest("api:key")
```

or

```python
AblyRest(token="token.string")
```

```python
AblyRest(key="api:key", rest_host="custom.host", port=8080)
```

## Support, feedback and troubleshooting

Please visit http://support.ably.io/ for access to our knowledgebase and to ask for any assistance.

You can also view the [community reported Github issues](https://github.com/ably/ably-python/issues).

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Ensure you have added suitable tests and the test suite is passing(`nosetests`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request

## License

Copyright (c) 2015 Ably Real-time Ltd, Licensed under the Apache License, Version 2.0.  Refer to [LICENSE](LICENSE) for the license terms.
