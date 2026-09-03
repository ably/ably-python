import base64
import os
import platform

import ably_pubsub.core

# The agent identifier for this library, sent with its version on every HTTP
# request and websocket handshake. Registered in the ably-common agents
# registry; renaming it partitions this SDK's traffic from its own history, so
# it changes only alongside a registry entry.
LIBRARY_AGENT_IDENTIFIER = 'ably-pubsub-python'

RUNTIME_AGENT_IDENTIFIER = 'python'


def _render_agents(agents):
    """Render an ``{identifier: version}`` mapping as Ably-Agent tokens.

    A ``None`` version renders as a bare flag, matching how the agents registry
    records entries that carry no version of their own (`browser`, and the
    side-declaring entries such as `ably-pubsub-server`).
    """
    return [name if version is None else f'{name}/{version}' for name, version in agents.items()]


class HttpUtils:
    default_format = "json"

    mime_types = {
        "json": "application/json",
        "xml": "application/xml",
        "html": "text/html",
        "binary": "application/x-msgpack",
    }

    @staticmethod
    def default_get_headers(binary=False, version=None, agents=None):
        headers = HttpUtils.default_headers(version=version, agents=agents)
        if binary:
            headers["Accept"] = HttpUtils.mime_types['binary']
        else:
            headers["Accept"] = HttpUtils.mime_types['json']
        return headers

    @staticmethod
    def default_post_headers(binary=False, version=None, agents=None):
        headers = HttpUtils.default_get_headers(binary=binary, version=version, agents=agents)
        headers["Content-Type"] = headers["Accept"]
        return headers

    @staticmethod
    def get_host_header(host):
        return {
            'Host': host,
        }

    @staticmethod
    def default_headers(version=None, agents=None):
        if version is None:
            version = ably_pubsub.core.api_version
        tokens = [
            f'{LIBRARY_AGENT_IDENTIFIER}/{ably_pubsub.core.lib_version}',
            f'{RUNTIME_AGENT_IDENTIFIER}/{platform.python_version()}',
        ]
        tokens.extend(_render_agents(agents or {}))
        return {
            "X-Ably-Version": version,
            "Ably-Agent": ' '.join(tokens),
        }

    @staticmethod
    def get_query_params(options):
        params = {}

        if options.add_request_ids:
            params['request_id'] = base64.urlsafe_b64encode(os.urandom(12)).decode('ascii')

        return params
