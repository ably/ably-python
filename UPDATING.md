# Upgrade / Migration Guide

## Version 1.1.1 to 1.2.0

We have made **breaking changes** in the version 1.2 release of this SDK.

In this guide we aim to highlight the main differences you will encounter when migrating your code from the interfaces we were offering prior to the version 1.2.0 release.

These include:

 - Deprecation of support for Python versions 3.4, 3.5 and 3.6
 - New, asynchronous API

### Deprecation of Python 3.4, 3.5 and 3.6

The minimum version of Python has increased to 3.7.
You may need to upgrade your environment in order to use this newer version of this SDK.
To see which versions of Python we test the SDK against, please look at our
[GitHub workflows](.github/workflows).

### Asynchronous API

The 1.2.0 version introduces a breaking change, which changes the way of interacting with the SDK from synchronous to asynchronous, using [the `asyncio` foundational library](https://docs.python.org/3.7/library/asyncio.html) to provide support for `async`/`await` syntax.
Because of this breaking change, every call that interacts with the Ably REST API must be refactored to this asynchronous way.

#### Publishing Messages

This old style, synchronous example:

```python
from ably import AblyRest

def main():
    ably = AblyRest('api:key')
    channel = ably.channels.get("channel_name")
    channel.publish('event', 'message')

if __name__ == "__main__":
    main()
```

Must now be replaced with this new style, asynchronous form:

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

#### Querying History

This old style, synchronous example:

```python
message_page = channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
message_page.next().items # List with messages from the second page
```

Must now be replaced with this new style, asynchronous form:

```python
message_page = await channel.history() # Returns a PaginatedResult
message_page.items # List with messages from this page
message_page.has_next() # => True, indicates there is another page
next_page = await message_page.next() # Returns a next page
next_page.items # List with messages from the second page
```

#### Querying Presence Members on a Channel

This old style, synchronous example:

```python
members_page = channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

Must now be replaced with this new style, asynchronous form:

```python
members_page = await channel.presence.get() # Returns a PaginatedResult
members_page.items
members_page.items[0].client_id # client_id of first member present
```

#### Querying Channel Presence History

This old style, synchronous example:

```python
presence_page = channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

Must now be replaced with this new style, asynchronous form:

```python
presence_page = await channel.presence.history() # Returns a PaginatedResult
presence_page.items
presence_page.items[0].client_id # client_id of first member
```

#### Generating a Token

This old style, synchronous example:

```python
token_details = client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
```

Must now be replaced with this new style, asynchronous form:

```python
token_details = await client.auth.request_token()
token_details.token # => "xVLyHw.CLchevH3hF....MDh9ZC_Q"
new_client = AblyRest(token=token_details)
await new_client.close()
```

#### Generating a TokenRequest

This old style, synchronous example:

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

Must now be replaced with this new style, asynchronous form:

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

#### Fetching Application Statistics

This old style, synchronous example:

```python
stats = client.stats() # Returns a PaginatedResult
stats.items
```

Must now be replaced with this new style, asynchronous form:

```python
stats = await client.stats() # Returns a PaginatedResult
stats.items
await client.close()
```

#### Fetching the Ably Service Time

This old style, synchronous example:

```python
client.time()
```

Must now be replaced with this new style, asynchronous form:

```python
await client.time()
await client.close()
```
