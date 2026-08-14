# Ably Pub/Sub Python SDK for servers

The Ably Pub/Sub client for servers: trusted environments which typically authenticate with an API key, and whose connections are exempt from monthly-active-user counting.

This package adds `ably.pubsub.server` to [`ably`](https://pypi.org/project/ably/), whose public surface it re-exports in full. If your application runs on an end-user device instead, use [`ably-pubsub-device`](https://pypi.org/project/ably-pubsub-device/).

## Installation

```sh
pip install ably-pubsub-server
```

## Usage

Use `create_realtime_client()` when the server needs a persistent connection — subscribing to channels, or entering presence:

```python
from ably.pubsub.server import create_realtime_client

async with create_realtime_client('your-ably-api-key') as client:
    channel = client.channels.get('test-channel')
    await channel.publish('test-event', 'hello world')
```

Use `create_http_client()` when publish, history, presence reads, stats and token issuing over HTTP are enough:

```python
from ably.pubsub.server import create_http_client

client = create_http_client('your-ably-api-key')
await client.channels.get('test-channel').publish('test-event', 'hello world')
```

A synchronous HTTP client, for servers that do not run an event loop, is available from the `sync` submodule:

```python
from ably.pubsub.server.sync import create_http_client

client = create_http_client('your-ably-api-key')
client.channels.get('test-channel').publish('test-event', 'hello world')
```

These factories take the same arguments as `ably.AblyRealtime` and `ably.AblyRest`, and behave identically to them.

## Migrating

Constructing `AblyRest` or `AblyRealtime` directly still works, but the factories name the side your application runs on. Replace:

| Before | After |
|--------|-------|
| `ably.AblyRest(...)` | `ably.pubsub.server.create_http_client(...)` |
| `ably.AblyRealtime(...)` | `ably.pubsub.server.create_realtime_client(...)` |
| `ably.sync.AblyRestSync(...)` | `ably.pubsub.server.sync.create_http_client(...)` |

## Support, feedback, and troubleshooting

For help or technical support, visit Ably's [support page](https://ably.com/support) or [GitHub Issues](https://github.com/ably/ably-python/issues).
