![Ably Pub/Sub Python Header](images/pythonSDK-github.png)
[![PyPI version](https://badge.fury.io/py/ably-pubsub-server.svg)](https://pypi.org/project/ably-pubsub-server/)
[![License](https://img.shields.io/github/license/ably/ably-python)](https://github.com/ably/ably-python/blob/main/LICENSE)


# Ably Pub/Sub Python SDK

Build any realtime experience using Ably’s Pub/Sub Python SDK.

Ably Pub/Sub provides flexible APIs that deliver features such as pub-sub messaging, message history, presence, and push notifications. Utilizing Ably’s realtime messaging platform, applications benefit from its highly performant, reliable, and scalable infrastructure.

Find out more:

* [Ably Pub/Sub docs.](https://ably.com/docs/basics)
* [Ably Pub/Sub examples.](https://ably.com/examples?product=pubsub)

---

## Getting started

Everything you need to get started with Ably:

* [Getting started with Pub/Sub using Python.](https://ably.com/docs/getting-started/python)
* [SDK Setup for Python.](https://ably.com/docs/getting-started/setup?lang=python)

---

## Packages

Python is a server-side language, so this repository publishes one package for
applications to install, plus the shared implementation it is built on:

| Distribution | For | Import |
| --- | --- | --- |
| `ably-pubsub-server` | Servers, backends, jobs — any trusted environment holding an API key | `ably_pubsub.server` |
| `ably-pubsub-core` | **Internal.** Ably's own packages only — never depend on it directly | — |

Installing the package that names the side your code runs on is more than a
naming convention: clients created by `ably-pubsub-server` declare themselves as
server-side on the wire, and server connections are exempt from monthly-active-user
counting.

Nothing under `ably_pubsub.core` is public API — its module layout and the names
within it may change in any release. Everything supported is re-exported from
`ably_pubsub.server`. The two distributions are versioned and released in
lockstep: `ably-pubsub-server` pins `ably-pubsub-core` to the exact same version.

---

## Supported platforms

Ably aims to support a wide range of platforms. If you experience any compatibility issues, open an issue in the repository or contact [Ably support](https://ably.com/support).

The following platforms are supported:

| Platform | Support                  |
|----------|--------------------------|
| Python | Python 3.8 through 3.14 |

> [!NOTE]
> This SDK works across all major operating platforms (Linux, macOS, Windows) as long as Python 3.8 or greater is available.

> [!IMPORTANT]
> The `ably` package (3.x and earlier) is superseded by `ably-pubsub-server`. See [Migrating from `ably` 3.x](#migrating-from-ably-3x).

---

## Installation

To get started with your project, install the package:

```sh
pip install ably-pubsub-server
```

> [!NOTE]
Install [Python](https://www.python.org/downloads/) version 3.8 or greater.

Optional extras: `crypto` for channel encryption, `vcdiff` for delta decoding,
and `oldcrypto` for the legacy `pycrypto` backend.

```sh
pip install "ably-pubsub-server[crypto]"
```

---

## Usage

Clients are created through the factory functions in `ably_pubsub.server`. They
take exactly the arguments the client constructors take, and return the same
clients.

### Realtime client

Connects to Ably's realtime messaging service, subscribes to a channel to
receive messages, and publishes a test message to that same channel.

```python
import asyncio
from ably_pubsub.server import create_realtime_client


async def main():
    realtime_client = create_realtime_client(key='your-ably-api-key', client_id='me')
    await realtime_client.connection.once_async('connected')
    print('Connected to Ably')

    channel = realtime_client.channels.get('test-channel')

    def on_message(message):
        print(f'Received message: {message.data}')

    await channel.subscribe(on_message)
    await channel.publish('test-event', 'hello world')

    await realtime_client.close()

asyncio.run(main())
```

### HTTP client

For publishing, history, presence reads, stats and token issuing, with no
persistent connection:

```python
import asyncio
from ably_pubsub.server import create_http_client


async def main():
    async with create_http_client(key='your-ably-api-key') as client:
        channel = client.channels.get('test-channel')
        await channel.publish('test-event', 'hello world')

asyncio.run(main())
```

### Synchronous HTTP client

For code that has no event loop. There is no synchronous realtime client.

```python
from ably_pubsub.server.sync import create_http_client

client = create_http_client(key='your-ably-api-key')
client.channels.get('test-channel').publish('test-event', 'hello world')
client.close()
```

---

## Migrating from `ably` 3.x

Version 4.0.0 moves the SDK to the `ably-pubsub-server` distribution and the
`ably_pubsub.server` import namespace. For most applications the change is
confined to the install line, the import, and the constructor call.
[UPDATING.md](./UPDATING.md) has the full mapping table and worked examples.

The `ably` package receives security and critical-bug fixes only for one year
from the 4.0.0 release, and is then end-of-life. The two packages can be
installed side by side while you migrate — they use different import packages.

---

## Releases

The [CHANGELOG.md](https://github.com/ably/ably-python/blob/main/CHANGELOG.md) contains details of the latest releases for this SDK. You can also view all Ably releases on [changelog.ably.com](https://changelog.ably.com).

---

## Contribute

Read the [CONTRIBUTING.md](./CONTRIBUTING.md) guidelines to contribute to Ably.

---

## Support, feedback, and troubleshooting

For help or technical support, visit Ably's [support page](https://ably.com/support) or [GitHub Issues](https://github.com/ably/ably-python/issues) for community-reported bugs and discussions.
