from __future__ import absolute_import

import json
import os

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

rest_host = os.environ.get('WEBSOCKET_ADDRESS')

if rest_host is None:
    rest_host = "staging-rest.ably.io"
    encrypted = True
    rest_port = 443
else:
    encrypted = not rest_host.equals("localhost")
    rest_port = 8081 if encrypted else 8080


class RestSetup:
    _test_vars = None

    ably = AblyRest(app_id="fakeAppId",
            rest_host=rest_host,
            rest_port=rest_port,
            encrypted=encrypted)

    @staticmethod
    def get_test_vars():
        if not RestSetup._test_vars:
            r = RestSetup.ably.post("/apps")

        return RestSetup._test_vars

    @staticmethod
    def clear_test_vars():
        RestSetup._test_vars = None
        RestSetup.ably = AblyRest(app_id="fakeAppId",
            rest_host=rest_host,
            rest_port=rest_port,
            encrypted=encrypted)

