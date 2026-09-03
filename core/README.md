# ably-pubsub-core

**This is an internal implementation package. Do not depend on it directly.**

`ably-pubsub-core` holds the shared implementation of Ably's Pub/Sub SDK for
Python: the HTTP and realtime clients, channels, presence, authentication,
encryption and the message types. It is published so that the packages
applications *do* install can depend on one shared implementation, pinned to an
exact version.

Install the package that names the side your code runs on instead:

| Where your code runs | Install | Import |
| --- | --- | --- |
| A server or other trusted environment | `ably-pubsub-server` | `ably_pubsub.server` |

Nothing under `ably_pubsub.core` is public API. Its module layout, and the
names within it, may change in any release — including patch releases — without
a deprecation cycle. The supported surface is what `ably_pubsub.server`
re-exports.

`ably_pubsub` is a [PEP 420](https://peps.python.org/pep-0420/) namespace
package: this distribution ships `ably_pubsub/core/**` and never
`ably_pubsub/__init__.py`, so other distributions can contribute their own
subpackages to the same namespace.

## Contributing

See [CONTRIBUTING.md](https://github.com/ably/ably-python/blob/main/CONTRIBUTING.md).

## License

Apache License 2.0 — see [LICENSE](https://github.com/ably/ably-python/blob/main/LICENSE).
