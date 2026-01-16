# API Reference Overview

The Ably Python SDK provides two main client interfaces:

## Core Clients

### [REST Client](rest.md)

The REST client (`AblyRest`) provides synchronous access to Ably's REST API:

- Publish messages to channels
- Query message history
- Manage channel lifecycle
- Retrieve statistics
- Token authentication

Use the REST client when you need simple request/response operations without maintaining a persistent connection.

### [Realtime Client](realtime.md)

The Realtime client (`AblyRealtime`) maintains a persistent connection to Ably:

- Subscribe to channels and receive messages in real-time
- Publish messages
- Monitor connection state
- Track presence
- Receive live updates

Use the Realtime client for applications that need live updates and bidirectional communication.

## Key Components

### [Authentication](auth.md)

The `Auth` class handles authentication with Ably, supporting:

- API key authentication
- Token authentication
- Token generation and renewal

### [Channels](channels.md)

Channel interfaces provide access to messaging functionality:

- REST channels for publishing and history
- Realtime channels for subscribing to messages
- Channel state management

### [Messages](messages.md)

Message types represent the data sent through Ably:

- `Message` - Standard pub/sub messages
- `PresenceMessage` - Presence state changes
- Encoding and encryption support

### [Types](types.md)

Core data types and configuration:

- `ClientOptions` - Client configuration
- `TokenDetails` - Authentication tokens
- `Stats` - Usage statistics
- Channel and connection options

### [Utilities](util.md)

Utility functions and helpers:

- Exception types
- Encoding/decoding utilities
- Cryptographic functions

## Client Capabilities

Both clients share common capabilities:

- **Auto-reconnection**: Automatic connection recovery
- **Message queueing**: Queues messages during disconnection
- **Type safety**: Full type hints for IDE support
- **Async/await support**: Native async support in Realtime client
- **Error handling**: Comprehensive error types