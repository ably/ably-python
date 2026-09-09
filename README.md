![Ably Pub/Sub Python Header](images/pythonSDK-github.png)
[![PyPI version](https://badge.fury.io/py/ably.svg)](https://pypi.org/project/ably/)
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

## Supported platforms

Ably aims to support a wide range of platforms. If you experience any compatibility issues, open an issue in the repository or contact [Ably support](https://ably.com/support).

The following platforms are supported:

| Platform | Support                  |
|----------|--------------------------|
| Python | Python 3.7+ through 3.14 |

> [!NOTE]
> This SDK works across all major operating platforms (Linux, macOS, Windows) as long as Python 3.7+ is available.

> [!IMPORTANT]
> SDK versions < 2.0.0 are [deprecated](https://ably.com/docs/platform/deprecate/protocol-v1).

---

## Installation

Install the package for the side your application runs on. Each pulls in `ably` and adds an entry point under `ably.pubsub` naming that side:

```sh
# Trusted server environments — publishing, token issuing, backend subscribers
pip install ably-pubsub-server   # provides ably.pubsub.server

# End-user devices — desktop apps, CLIs, IoT and embedded clients
pip install ably-pubsub-device   # provides ably.pubsub.device
```

Installing `ably` on its own also still works, and remains fully supported. It is the shared core both build on, and the clients they return are its clients unchanged.

> [!NOTE]
Install [Python](https://www.python.org/downloads/) version 3.8 or greater.

## Usage

The following code connects to Ably's realtime messaging service, subscribes to a channel to receive messages, and publishes a test message to that same channel.

```python
from ably.pubsub.device import create_client

# Initialize Ably Realtime client
async with create_client('your-ably-api-key', client_id='me') as realtime_client:
    # Wait for connection to be established
    await realtime_client.connection.once_async('connected')
    print('Connected to Ably')
    
    # Get a reference to the 'test-channel' channel
    channel = realtime_client.channels.get('test-channel')
    
    # Subscribe to all messages published to this channel
    def on_message(message):
        print(f'Received message: {message.data}')
    
    await channel.subscribe(on_message)
    
    # Publish a test message to the channel
    await channel.publish('test-event', 'hello world')
```

On a server, use `ably.pubsub.server.create_realtime_client()` for the same client over a persistent connection, or `ably.pubsub.server.create_http_client()` when publish, history, presence reads, stats and token issuing over HTTP are enough. A synchronous HTTP client is available from `ably.pubsub.server.sync`.

### Migrating from the AblyRest and AblyRealtime constructors

Constructing `ably.AblyRest` or `ably.AblyRealtime` directly still works and is not scheduled for removal, but it emits a `DeprecationWarning` pointing at the factory for your side:

| Before | After |
|--------|-------|
| `ably.AblyRealtime(...)` on a device | `ably.pubsub.device.create_client(...)` |
| `ably.AblyRealtime(...)` on a server | `ably.pubsub.server.create_realtime_client(...)` |
| `ably.AblyRest(...)` | `ably.pubsub.server.create_http_client(...)` |
| `ably.sync.AblyRestSync(...)` | `ably.pubsub.server.sync.create_http_client(...)` |

The factories take the same arguments as the constructors they replace and behave identically to them, so migrating is a change of entry point only.

## Releases

The [CHANGELOG.md](https://github.com/ably/ably-python/blob/main/CHANGELOG.md) contains details of the latest releases for this SDK. You can also view all Ably releases on [changelog.ably.com](https://changelog.ably.com).

---

## Contribute

Read the [CONTRIBUTING.md](./CONTRIBUTING.md) guidelines to contribute to Ably.

---

## Support, feedback, and troubleshooting

For help or technical support, visit Ably's [support page](https://ably.com/support) or [GitHub Issues](https://github.com/ably/ably-python/issues) for community-reported bugs and discussions.

### Full Realtime support unavailable

This SDK currently supports only [Ably REST](https://ably.com/docs/rest) and basic realtime message subscriptions. To access full [Ably Realtime](https://ably.com/docs/realtime) features in Python, consider using the [MQTT adapter](https://ably.com/docs/mqtt).

