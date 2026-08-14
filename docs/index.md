# Ably Python SDK Documentation

Build any realtime experience using Ably's Pub/Sub Python SDK.

Ably Pub/Sub provides flexible APIs that deliver features such as pub-sub messaging, message history, presence, and push notifications. Utilizing Ably's realtime messaging platform, applications benefit from its highly performant, reliable, and scalable infrastructure.

## Quick Links

* [Ably Pub/Sub docs](https://ably.com/docs/basics)
* [Ably Pub/Sub examples](https://ably.com/examples?product=pubsub)
* [GitHub Repository](https://github.com/ably/ably-python)

## Supported Platforms

The Ably Python SDK supports Python 3.7+ across all major operating platforms (Linux, macOS, Windows).

!!! important
    SDK versions < 2.0.0-beta.6 are [deprecated](https://ably.com/docs/platform/deprecate/protocol-v1).

## Installation

Install the package using pip:

```bash
pip install ably
```

## Quick Start

The following code connects to Ably's realtime messaging service, subscribes to a channel to receive messages, and publishes a test message to that same channel:

```python
from ably import AblyRealtime

# Initialize Ably Realtime client
async with AblyRealtime('your-ably-api-key', client_id='me') as realtime_client:
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

## Features

- **REST API**: Complete REST API support for publishing messages, querying history, and managing channels
- **Realtime Messaging**: Subscribe to channels and receive messages in real-time
- **Authentication**: Support for API keys, tokens, and token authentication
- **Message History**: Query historical messages from channels
- **Presence**: Track presence of clients on channels
- **Push Notifications**: Send push notifications to devices
- **Type Safety**: Full type hints for better IDE support

## Support

For help or technical support:

- Visit [Ably's support page](https://ably.com/support)
- Report issues on [GitHub Issues](https://github.com/ably/ably-python/issues)
