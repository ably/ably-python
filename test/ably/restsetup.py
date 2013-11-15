from __future__ import absolute_import

import json
import os
import logging

import requests

from ably.exceptions import AblyException
from ably.rest import AblyRest

app_spec_text = ""
log = logging.getLogger(__name__)

with open(os.path.dirname(__file__) + '/../assets/testAppSpec.json', 'r') as f:
    app_spec_text = f.read()

print app_spec_text

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
            r = requests.post("%s/apps" % ably.authority, headers=ably._default_post_headers(),
                    data=app_spec_text)
            AblyException.raise_for_response(r)

            app_spec = r.json()
            app_id = app_spec.get("id", "")

            test_vars = {
                "app_id": app_id,
                "host": host,
                "port": port,
                "tls_port": tls_port,
                "encrypted": encrypted,
                "keys": [{
                    "key_id": "%s.%s" % (app_id, k.get("id", "")),
                    "key_value": k.get("value", ""),
                    "key_str": "%s.%s:%s" % (app_id, k.get("id", ""), k.get("value", "")),
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

        log.info(str(test_vars))
        headers = ably._default_get_headers()
        ably._delete('/apps/' + test_vars['app_id'], headers)

        RestSetup.__test_vars = None

log.info(str(RestSetup.get_test_vars()))
