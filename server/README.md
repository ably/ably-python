# ably-pubsub-server

The [Ably](https://ably.com) Pub/Sub SDK for Python **servers** — backends, jobs,
and any other trusted environment that holds an API key.

Ably is the platform that powers synchronized digital experiences in realtime.
Pub/Sub is its foundational product: publish and subscribe messaging over
channels, presence, history, and token issuing.

Choosing the package by side matters beyond naming: connections made by this
package declare themselves as server-side on the wire, and server connections
are exempt from monthly-active-user counting.

## Installation

```shell
pip install ably-pubsub-server
```

Optional extras: `crypto` (channel encryption, via pycryptodome) and `vcdiff`
(delta decoding).

```shell
pip install "ably-pubsub-server[crypto]"
```

## Usage

Create clients through the factory functions — they are the entry points of this
package.

```python
from ably_pubsub.server import create_http_client, create_realtime_client
```

### Stateless HTTP client

For publishing, history, presence reads, stats and token issuing:

```python
import asyncio
from ably_pubsub.server import create_http_client


async def main():
    async with create_http_client(key='your-api-key') as client:
        channel = client.channels.get('some-channel')
        await channel.publish('greeting', 'hello')

asyncio.run(main())
```

A synchronous flavour of the HTTP client is available for code that has no event
loop:

```python
from ably_pubsub.server.sync import create_http_client

client = create_http_client(key='your-api-key')
client.channels.get('some-channel').publish('greeting', 'hello')
```

### Realtime client

When the server also needs to subscribe to channels or enter presence over a
persistent connection:

```python
import asyncio
from ably_pubsub.server import create_realtime_client


async def main():
    client = create_realtime_client(key='your-api-key')
    channel = client.channels.get('some-channel')
    await channel.subscribe(lambda message: print(message.data))
    await asyncio.sleep(10)
    await client.close()

asyncio.run(main())
```

There is no synchronous realtime client.

## Relationship to other packages

- `ably-pubsub-core` — the shared implementation this package is built on. It is
  an internal package; do not import `ably_pubsub.core` directly. Everything
  supported is re-exported from `ably_pubsub.server`.
- `ably` — the 3.x package this one replaces. See
  [UPDATING.md](https://github.com/ably/ably-python/blob/main/UPDATING.md).

## Contributing

See [CONTRIBUTING.md](https://github.com/ably/ably-python/blob/main/CONTRIBUTING.md).

## License

Apache License 2.0 — see [LICENSE](https://github.com/ably/ably-python/blob/main/LICENSE).
