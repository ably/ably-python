# Upgrade / Migration Guide

## Version 1.1.1 to 1.2.0

We have made **breaking changes** in the version 1.2 release of this SDK.

In this guide we aim to highlight the main differences you will encounter when migrating your code from the interfaces we were offering
prior to the version 1.2.0 release.

These include:
 - Deprecating Python 3.4
 - Introduction of Asynchronous way of using the SDK

### Using the SDK API in synchronous way

This way using it is still possible. In order to use SDK in synchronous way please use the <= 1.1.0 version of this SDK.

### Deprecating Python 3.4

This python version is already not supported, hence we decided to drop support of this version. Please upgrade your environment in order
to use the 1.2.x version.


### Introduction of Asynchronous way of using the SDK

The 1.2.x version introduces breaking change, which aims to change way of interacting with the SDK from Synchronous way to Asynchronous. Because of that
every call that is interacting with the Ably Rest API must be done in asynchronous way.

#### Synchronous way of using the sdk with publishing sample message

```python
from ably import AblyRest

def main():
    ably = AblyRest('api:key')
    channel = ably.channels.get("channel_name")
    channel.publish('event', 'message')


if __name__ == "__main__":
    main()
```

#### Asynchronous way

```python
import asyncio
from ably import AblyRest

async def main():
    async with AblyRest('api:key') as ably:
        channel = ably.channels.get("channel_name")
        await channel.publish('event', 'message')


if __name__ == "__main__":
    asyncio.run(main())
```

#### Synchronous way of querying the history

```python
message_page = channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
message_page.next().items # List with messages from the second page
```

#### Asynchronous way

```python
message_page = await channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
next_page = await message_page.next() # Returns a next page
next_page.items # List with messages from the second page
```

#### Synchronous way of querying presence members on a channel

```python
members_page = channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

#### Asynchronous way

```python
members_page = await channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

#### Synchronous way of querying the presence of history

```python
presence_page = channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

#### Asynchronous way

```python
presence_page = await channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

#### Synchronous way of generating a token

```python
token_details = client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
```

#### Asynchronous way

```python
token_details = await client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
await new_client.close()
```

#### Synchronous way of generating a TokenRequest

```python
token_request = client.auth.create_token_request(
    {
        'client_id': 'jim',
        'capability': {'channel1': '"*"'},
        'ttl': 3600 * 1000, # ms
    }
)

new_client = AblyRest(token=token_request)
```

#### Asynchronous way

```python
token_request = await client.auth.create_token_request(
    {
        'client_id': 'jim',
        'capability': {'channel1': '"*"'},
        'ttl': 3600 * 1000, # ms
    }
)

new_client = AblyRest(token=token_request)
await new_client.close()
```

#### Synchronous way of fetching your application's stats

```python
stats = client.stats() # Returns a PaginatedResult
stats.items
```

#### Asynchronous way

```python
stats = await client.stats() # Returns a PaginatedResult
stats.items
await client.close()
```

#### Synchronous way of fetching the Ably service time

```python
client.time()
```

#### Asynchronous way

```python
await client.time()
await client.close()
```