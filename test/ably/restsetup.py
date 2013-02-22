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

rest_host = os.environ.get('WEBSOCKET_ADDRESS')

if rest_host is None:
    rest_host = "staging-rest.ably.io"
    encrypted = True
    rest_port = 443
else:
    encrypted = not rest_host.equals("localhost")
    rest_port = 8081 if encrypted else 8080

ably = AblyRest(app_id="fakeAppId",
        rest_host=rest_host,
        rest_port=rest_port,
        encrypted=encrypted)


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

            app_id = app_spec.get("id", "")
            test_vars = {
                "rest_host": rest_host,
                "rest_port": rest_port,
                "encrypted": encrypted,
                "app_id": app_id,
                "keys": [{
                    "key_id": k.get("id", ""),
                    "key_value": k.get("value", ""),
                    "key_str": "%s:%s:%s" % (app_id, k.get("id", ""), k.get("value", "")),
                    "capability": k.get("capability", ""),
                } for k in app_spec.get("keys", [])]
            }

            RestSetup.__test_vars = test_vars

        return RestSetup.__test_vars

    @staticmethod
    def clear_test_vars():
        test_vars = RestSetup.__test_vars
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                rest_host=test_vars["rest_host"],
                rest_port=test_vars["rest_port"],
                encrypted=test_vars["encrypted"])

        ably._delete('')

        RestSetup.__test_vars = None

