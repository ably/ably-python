ably-python
-----------

[![Coverage Status](https://coveralls.io/repos/ably/ably-python/badge.svg?branch=master&service=github)](https://coveralls.io/github/ably/ably-python?branch=master)

A Python client library for [www.ably.io](https://www.ably.io), the realtime messaging service.

Works with Python 2.7 and 3.4 onwards.

User support for older Python 3.2 and 3.3 versions is still provided through
Github issues and pull requests.

## Documentation

Visit https://www.ably.io/documentation for a complete API reference and more examples.

## Installation

The client library is available as a [PyPI package](https://pypi.python.org/pypi/ably).

### From PyPI

    pip install ably

Or, if you need encryption features:

    pip install 'ably[crypto]'

### Locally

    git clone https://github.com/ably/ably-python.git
    cd ably-python
    python setup.py install

## Using the REST API

All examples assume a client and/or channel has been created as follows:

```python
from ably import AblyRest
client = AblyRest('api:key')
channel = client.channels.get('channel_name')
```

### Publishing a message to a channel

```python
channel.publish('event', 'message')
```

### Querying the History

```python
message_page = channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
message_page.next().items # List with messages from the second page
```

### Current presence members on a channel

```python
members_page = channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

### Querying the presence history

```python
presence_page = channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

### Symmetric end-to-end encrypted payloads on a channel

When a 128 bit or 256 bit key is provided to the library, all payloads are encrypted and decrypted automatically using that key on the channel. The secret key is never transmitted to Ably and thus it is the developer's responsibility to distribute a secret key to both publishers and subscribers.

```ruby
key = ably.util.crypto.generate_random_key()
channel = rest.channels.get('communication', cipher={'key': key})
channel.publish(u'unencrypted', u'encrypted secret payload')
messages_page = channel.history()
messages_page.items[0].data #=> "sensitive data"
```

### Generate a Token

Tokens are issued by Ably and are readily usable by any client to connect to Ably:

```python
token_details = client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
```

### Generate a TokenRequest

Token requests are issued by your servers and signed using your private API key. This is the preferred method of authentication as no secrets are ever shared, and the token request can be issued to trusted clients without communicating with Ably.

```python
token_request = client.auth.create_token_request(
    {
        'client_id': 'jim',
        'capability': {'channel1': '"*"'},
        'ttl': 3600,
    }
)
# => {"id": ...,
#     "clientId": "jim",
#     "ttl": 3600,
#     "timestamp": ...,
#     "capability": "{\"*\":[\"*\"]}",
#     "nonce": ...,
#     "mac": ...}

new_client = AblyRest(token=token_request)
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

To see what has changed in recent versions of Bundler, see the [CHANGELOG](CHANGELOG.md).

## Running the test suite

```python
git submodule init
git submodule update
pip install -r requirements-test.txt
pytest test
```

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Ensure you have added suitable tests and the test suite is passing(`py.test`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create a new Pull Request

## Release Process

1. Update [`setup.py`](./setup.py) with the new version number
2. Run `python setup.py sdist upload -r pypi` to build and upload this new package to PyPi
3. Run [`github_changelog_generator`](https://github.com/skywinder/Github-Changelog-Generator) to automate the update of the [CHANGELOG](./CHANGELOG.md). Once the CHANGELOG has completed, manually change the `Unreleased` heading and link with the current version number such as `v1.0.0`. Also ensure that the `Full Changelog` link points to the new version tag instead of the `HEAD`. Commit this change.
4. Tag the new version such as `git tag v1.0.0`
5. Visit https://github.com/ably/ably-python/tags and add release notes for the release including links to the changelog entry.
6. Push the tag to origin `git push origin v1.0.0`

## License

Copyright (c) 2016 Ably Real-time Ltd, Licensed under the Apache License, Version 2.0.  Refer to [LICENSE](LICENSE) for the license terms.
