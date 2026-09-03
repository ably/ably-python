# ably-pubsub-server

The [Ably](https://ably.com) Pub/Sub SDK for Python **servers** — backends, jobs,
and any other trusted environment that holds an API key.

Ably is the platform that powers synchronized digital experiences in realtime.
Pub/Sub is its foundational product: publish and subscribe messaging over
channels, presence, history, and token issuing.

## What this package is for

Install this package when your code runs somewhere you control and trust: a
backend service, an API, a worker or a scheduled job — anywhere that can hold an
API key. It is not for browsers, mobile apps, or anything else shipped to an end
user.

Choosing the package by side matters beyond naming. Clients created here stamp
`ably-pubsub-server` into the agent identifier they put on the wire — the wire
shape is `ably-pubsub-python/4.0.0 python/3.x ably-pubsub-server` — and that
flag is how the platform classifies the connection as server-side and exempts it
from monthly-active-user counting.

Requires Python 3.8 or greater.

## Installation

```shell
pip install ably-pubsub-server
```

Optional extras: `crypto` (channel encryption, via pycryptodome), `vcdiff`
(delta decoding) and `oldcrypto` (the legacy pycrypto backend).

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
client.close()
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

Both factories take exactly the arguments the underlying client constructors
take: `create_http_client(key=None, token=None, token_details=None, **options)`
and `create_realtime_client(key=None, loop=None, **options)`.

## Documentation

- [Ably Pub/Sub docs](https://ably.com/docs/basics)
- [Getting started with Pub/Sub using Python](https://ably.com/docs/getting-started/python)
- [Ably Pub/Sub examples](https://ably.com/examples?product=pubsub)

## Relationship to other packages

- `ably-pubsub-core` — the shared implementation this package is built on. It is
  an internal package; do not import `ably_pubsub.core` directly. Everything
  supported is re-exported from `ably_pubsub.server`.
- `ably` — the 3.x package this one replaces. It receives security and
  critical-bug fixes only for one year from the 4.0.0 release, and is then
  end-of-life. The migration is usually three lines: see
  [UPDATING.md](https://github.com/ably/ably-python/blob/main/UPDATING.md).

## Contributing

See [CONTRIBUTING.md](https://github.com/ably/ably-python/blob/main/CONTRIBUTING.md).

## License

Apache License 2.0 — see [LICENSE](https://github.com/ably/ably-python/blob/main/LICENSE).
