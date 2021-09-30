ably-python
-----------

![.github/workflows/check.yml](https://github.com/ably/ably-python/workflows/.github/workflows/check.yml/badge.svg)
[![PyPI version](https://badge.fury.io/py/ably.svg)](https://badge.fury.io/py/ably)


## Overview

This is a Python client library for Ably. The library currently targets the [Ably 1.1 client library specification](https://www.ably.io/documentation/client-lib-development-guide/features/).

## Running example

```python
import asyncio
from ably import AblyRest

async def main():
    async with AblyRest('api:key') as ably:
        channel = ably.channels.get("channel_name")

if __name__ == "__main__":
    asyncio.run(main())
```

## Installation

The client library is available as a [PyPI package](https://pypi.python.org/pypi/ably).

[Requirements](https://github.com/ably/ably-python#requirements)

### From PyPI

    pip install ably

Or, if you need encryption features:

    pip install 'ably[crypto]'

### Locally

    git clone https://github.com/ably/ably-python.git
    cd ably-python
    python setup.py install

## Breaking API Changes in Version 1.2.x

Please see our Upgrade / Migration Guide for notes on changes you need to make to your code to update it to use the new API
introduced by version 1.2.x

## Usage

All examples assume a client and/or channel has been created in one of the following ways:

With closing the client manually:

```python
from ably import AblyRest

async def main(): 
    client = AblyRest('api:key')
    channel = client.channels.get('channel_name')
    await client.close()
```

When using the client as a context manager, this will ensure that client is properly closed 
while leaving the `with` block:

```python
from ably import AblyRest

async def main():
    async with AblyRest('api:key') as ably:
        channel = ably.channels.get("channel_name")
```

You can define the logging level for the whole library, and override for a
specific module:
```python
import logging
import ably

logging.getLogger('ably').setLevel(logging.WARNING)
logging.getLogger('ably.rest.auth').setLevel(logging.INFO)
```
You need to add a handler to see any output:
```python
logger = logging.getLogger('ably')
logger.addHandler(logging.StreamHandler())
```
### Publishing a message to a channel

```python
await channel.publish('event', 'message')
```

### Querying the History

```python
message_page = await channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
next_page = await message_page.next() # Returns a next page
next_page.items # List with messages from the second page
```

### Current presence members on a channel

```python
members_page = await channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

### Querying the presence history

```python
presence_page = await channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

### Symmetric end-to-end encrypted payloads on a channel

When a 128 bit or 256 bit key is provided to the library, all payloads are encrypted and decrypted automatically using that key on the channel. The secret key is never transmitted to Ably and thus it is the developer's responsibility to distribute a secret key to both publishers and subscribers.

```python
key = ably.util.crypto.generate_random_key()
channel = rest.channels.get('communication', cipher={'key': key})
channel.publish(u'unencrypted', u'encrypted secret payload')
messages_page = await channel.history()
messages_page.items[0].data #=> "sensitive data"
```

### Generate a Token

Tokens are issued by Ably and are readily usable by any client to connect to Ably:

```python
token_details = await client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
await new_client.close()
```

### Generate a TokenRequest

Token requests are issued by your servers and signed using your private API key. This is the preferred method of authentication as no secrets are ever shared, and the token request can be issued to trusted clients without communicating with Ably.

```python
token_request = await client.auth.create_token_request(
    {
        'client_id': 'jim',
        'capability': {'channel1': '"*"'},
        'ttl': 3600 * 1000, # ms
    }
)
# => {"id": ...,
#     "clientId": "jim",
#     "ttl": 3600000,
#     "timestamp": ...,
#     "capability": "{\"*\":[\"*\"]}",
#     "nonce": ...,
#     "mac": ...}

new_client = AblyRest(token=token_request)
await new_client.close()
```

### Fetching your application's stats

```python
stats = await client.stats() # Returns a PaginatedResult
stats.items
await client.close()
```

### Fetching the Ably service time

```python
await client.time()
await client.close()
```

## Resources

Visit https://www.ably.io/documentation for a complete API reference and more examples.

## Requirements

This SDK supports Python 3.6+.

We regression-test the SDK against a selection of Python versions (which we update over time, 
but usually consists of mainstream and widely used versions). Please refer to [check.yml](.github/workflows/check.yml) 
for the set of versions that currently undergo CI testing.

## Known Limitations

Currently, this SDK only supports [Ably REST](https://www.ably.io/documentation/rest). 
However, you can use the [MQTT adapter](https://www.ably.io/documentation/mqtt) to implement [Ably's Realtime](https://www.ably.io/documentation/realtime) features using Python.

## Support, Feedback and Troubleshooting

If you find any compatibility issues, please [do raise an issue](https://github.com/ably/ably-python/issues/new) in this repository or [contact Ably customer support](https://support.ably.io/) for advice.

## Support, feedback and troubleshooting

Please visit http://support.ably.io/ for access to our knowledge base and to ask for any assistance.

You can also view the [community reported GitHub issues](https://github.com/ably/ably-python/issues).

To see what has changed in recent versions of Bundler, see the [CHANGELOG](CHANGELOG.md).

## Contributing

For guidance on how to contribute to this project, see [CONTRIBUTING.md](https://github.com/ably/ably-python/blob/main/CONTRIBUTING.md)
