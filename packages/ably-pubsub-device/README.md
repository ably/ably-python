# Ably Pub/Sub Python SDK for devices

The Ably Pub/Sub client for devices: applications running in end-user environments (desktop apps, IoT and embedded clients) whose connections are identified by a `client_id` and counted on accounts with monthly-active-user billing.

This package adds `ably.pubsub.device` to [`ably`](https://pypi.org/project/ably/), whose public surface it re-exports in full. If your application runs in a trusted server environment instead, use [`ably-pubsub-server`](https://pypi.org/project/ably-pubsub-server/).

## Installation

```sh
pip install ably-pubsub-device
```

## Usage

```python
from ably.pubsub.device import create_client

async with create_client('your-ably-api-key', client_id='me') as client:
    await client.connection.once_async('connected')

    channel = client.channels.get('test-channel')

    def on_message(message):
        print(f'Received message: {message.data}')

    await channel.subscribe(on_message)
    await channel.publish('test-event', 'hello world')
```

`create_client()` takes the same arguments as `ably.AblyRealtime`, and behaves identically to it.

## Migrating

Constructing `AblyRealtime` directly still works and is not scheduled for removal, but the factories name the side your application runs on. Replace `ably.AblyRealtime(...)` with `ably.pubsub.device.create_client(...)`.

## Support, feedback, and troubleshooting

For help or technical support, visit Ably's [support page](https://ably.com/support) or [GitHub Issues](https://github.com/ably/ably-python/issues).
