from __future__ import absolute_import

import json
import os

import requests

from ably.exceptions import AblyException
from ably.rest import AblyRest

test_app_spec = {
    "keys": [
        {}, # key 0, blanket
        {   # key 1, specific channel and ops
            "capability": json.dumps({
                "testchannel": ["publish"],
            }),
        },
        {   # key 2, wildcard channel spec
            "capability": json.dumps({
                "*": ["subscribe"],
                "canpublish:*": ["publish"],
                "canpublish:andpresence":["presence", "publish"],
            }),
        },
        {   # key 3, wildcard ops spec
            "capability": json.dumps({
                "candoall": ["*"],
            }),
        },
        {   # key 4, multiple resources
            "capability": json.dumps({
                "channel0": ["publish"],
                "channel1": ["publish"],
                "channel2": ["publish", "subscribe"],
                "channel3": ["subscribe"],
                "channel4": ["presence", "publish", "subscribe"],
                "channel5": ["presence"],
                "channel6": ["*"],
            }),
        },
        {   # key 5, has wildcard clientId
            "privileged": True,
            "capability": json.dumps({
                "channel0": ["publish"],
                "channel1": ["publish"],
                "channel2": ["publish", "subscribe"],
                "channel3": ["subscribe"],
                "channel4": ["presence", "publish", "subscribe"],
                "channel5": ["presence"],
                "channel6": ["*"],
            }),
        },
    ],
}

app_spec_text = json.dumps(test_app_spec)

tls = (os.environ.get('ABLY_TLS') or "true").lower() == "true"
host = os.environ.get('ABLY_HOST')

if host is None:
    host = "staging-rest.ably.io"

if host.endswith("rest.ably.io"):
    host = "staging-rest.ably.io"
    encrypted = tls
    port = 80
    tls_port = 443
else:
    encrypted = tls and not host.equals("localhost")
    port = 8080
    tls_port = 8081

ably = AblyRest(host=host,
        port=port,
        tls_port=tls_port,
        tls=encrypted)


class RestSetup:
    __test_vars = None

    @staticmethod
    def get_test_vars():
        if not RestSetup.__test_vars:
            r = requests.post("%s/apps" % ably.authority, 
                    headers=ably._default_post_headers(),
                    data=app_spec_text)
            AblyException.raise_for_response(r)

            app_spec = r.json()

            test_vars = {
                "host": host,
                "port": port,
                "tls_port": tls_port,
                "encrypted": encrypted,
                "keys": [{
                    "key_id": k.get("id", ""),
                    "key_value": k.get("value", ""),
                    "key_str": "%s:%s" % (k.get("id", ""), k.get("value", "")),
                    "capability": k.get("capability", ""),
                } for k in app_spec.get("keys", [])]
            }

            RestSetup.__test_vars = test_vars

        return RestSetup.__test_vars

    @staticmethod
    def clear_test_vars():
        test_vars = RestSetup.__test_vars
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["encrypted"])

        ably._delete('')

        RestSetup.__test_vars = None

