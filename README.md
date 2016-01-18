ably-python
-----------

[![Build Status](https://travis-ci.org/ably/ably-python.svg?branch=master)](https://travis-ci.org/ably/ably-python)
[![Coverage Status](https://coveralls.io/repos/ably/ably-python/badge.svg?branch=master&service=github)](https://coveralls.io/github/ably/ably-python?branch=master)

Ably.io Python client library - REST interface. Supports Python 2.7-3.5.

## Documentation

Visit https://www.ably.io/documentation for a complete API reference and more examples.

## Installation

### From PyPI (soon)

    pip install ably

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

## Using the REST API

All examples assume a client and/or channel has been created as follows:

```python
from ably import AblyRest
client = AblyRest('api:key')
channel = client.channels.channel_name
```

### Publishing a message to a channel

```python
channel.publish('event', 'message')
```

### Querying the History

```python
mesage_page = channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
message_page.next().items # List with messages from the second page
```

### Presence on a channel

```python
members_page = channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

### Querying the Presence History

```python
presence_page = channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

### Generate Token and Token Request

```python
token_details = client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details.token)

token_request = client.auth.create_token_request(
    {
        'id': 'id',
        'client_id': None,
        'capability': {'channel1': '"*"'},
        'ttl': 60000,
    }
)


```

### Fetching your application's stats

```python
stats = client.stats() # Returns a PaginatedResult
stats.items
```

### Fetching the Ably service time

```python
client.time()
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
