# Ably Python Client Library SDK: Roadmap

This document outlines our plans for the evolution of this SDK.

## Milestone 1: Realtime Channel Subscription

Once we've completed the scope and objectives detailed in this milestone,
we'll be in a good position to make a release in order to start getting feedback from customers.

### Milestone 1a: Solidify Existing Foundations

Ensure the current source code is in a good enough state to build upon.
This means solving currently known pain points (development environment stabilisation) as well as reassessing our baselines.

**Scope**:

- Resolve issues with dependency pinning
- Ensure linter is pulling its weight - state of the art changes fast in this area, so we should assess what rules are enabled, which are not, what we could be leveraging, etc..
- Check language and runtime requirements, in case any of them can be increased in order for us to be able to use more modern foundation features of Python

**Objective**: Achieve confidence that we have foundations we can confidently build upon, knowing what's coming up in future milestones.

### Milestone 1b: Establish Realtime Foundations and Connect

**Scope**:

- pick a WebSocket library
- pick an event model (async/await vs dedicated thread)
- establish connection with basic credentials (Ably API key)

**Objective**: Successfully connect to Ably Realtime.

### Milestone 1c: Realtime Connection Lifecycle

The basic foundations of Realtime connectivity, plus client identification (`Agent`).

**Scope**:

- send `Ably-Agent` header when establishing WebSocket connection ([`RSC7d2`](https://docs.ably.io/client-lib-development-guide/features/#RSC7d2))
- loop to read protocol messages from the WebSocket
- handle basic connectivity messages: `CONNECTED`, `DISCONNECTED`, `CLOSED`, `ERROR`
- handle `HEARTBEAT` messages
- queryable connection state
  - consider whether there is a Python-idiomatic alternative to blindly implementing `EventEmitter`

**Objective**: Track connection state and offer API to query it.

### Milestone 1d: Basic Realtime-Client-initiated Messages

Give our users some control.

**Scope**:

- client to service `CLOSE` ([`RTC16`](https://docs.ably.io/client-lib-development-guide/features/#RTC16))
- ping ([`RTN13`](https://docs.ably.io/client-lib-development-guide/features/#RTN13))
  - loop to read messages from user
  - send a ping (`HEARTBEAT`)
  - wait for a response (`HEARTBEAT`)
  - callback to user with timing info

**Objective**: Provide APIs for sending basic messages to the service,
resulting in proof-of-life / smoke-test proving interactions with the event model chosen in [1b](#milestone-1b-establish-realtime-foundations-and-connect).

### Milestone 1e: Attach and Subscribe

Start receiving messages from the Ably service.

**Scope**:

- channels, including:
  - attach ([`RTL4`](https://docs.ably.io/client-lib-development-guide/features/#RTL4))
  - detach ([`RTL5`](https://docs.ably.io/client-lib-development-guide/features/#RTL5))
  - subscribe ([RTL7](https://docs.ably.io/client-lib-development-guide/features/#RTL7)) / unsubscribe ([RTL8](https://docs.ably.io/client-lib-development-guide/features/#RTL8))
    - consider whether there is a Python-idiomatic alternative to blindly implementing `EventEmitter`

**Objective**: Receive application level messages from the network.

## Milestone 2: Realtime Connectivity Hardening

_T.B.D. but will include environments and connection resume._

## Milestone 3: Token Authentication

_T.B.D. but necessary in order to utilise capabilities embedded within signed JWTs for production applications._

## Milestone 3: Realtime Channel Publish

_T.B.D._

## Milestone 4: Realtime Channel Presence

_T.B.D._
