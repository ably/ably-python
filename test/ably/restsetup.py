from __future__ import absolute_import, print_function

import json
import os
import logging

from ably.http.httputils import HttpUtils
from ably.rest.rest import AblyRest
from ably.types.capability import Capability
from ably.types.options import Options
from ably.util.exceptions import AblyException

app_spec_text = ""
log = logging.getLogger(__name__)

with open(os.path.dirname(__file__) + '/../../ably-common/test-resources/test-app-setup.json', 'r') as f:
    app_spec_text = f.read()

post_apps_text = json.dumps(json.loads(app_spec_text)["post_apps"])
tls = (os.environ.get('ABLY_TLS') or "true").lower() == "true"
host = os.environ.get('ABLY_HOST')


if host is None:
    host = "sandbox-rest.ably.io"

if host.endswith("rest.ably.io"):
    host = "sandbox-rest.ably.io"
    port = 80
    tls_port = 443
else:
    tls = tls and not host.equals("localhost")
    port = 8080
    tls_port = 8081


#used for acquiring a keyId and value for testing
ably = AblyRest(Options(restHost=host,
        port=port,
        tls_port=tls_port,
        tls=tls,
        keyId="dummyId",
        keyValue="dummyValue"))


class RestSetup:
    __test_vars = None

    @staticmethod
    def testOptions(keyNumber=0):
        if not RestSetup.__test_vars:
            get_test_vars()

        key = RestSetup.__test_vars["keys"][keyNumber]["key_str"]
        keyComponents = key.split(':')
        keyId = keyComponents[0]
        keyValue = keyComponents[1]
        capability=RestSetup.__test_vars["keys"][keyNumber]["capability"]
        return Options(restHost=host, port=port, tls_port=tls_port,tls=tls,keyValue=keyValue,keyId=keyId, capability=capability)


    @staticmethod
    def get_test_vars(sender=None):

        if not RestSetup.__test_vars:
            r = ably.http.post("/apps", headers=HttpUtils.default_post_headers(),
                    body=post_apps_text, skip_auth=True)
            AblyException.raise_for_response(r)
            
            app_spec = r.json()
            
            app_id = app_spec.get("appId", "")

            test_vars = {
                "app_id": app_id,
                "host": host,
                "port": port,
                "tls_port": tls_port,
                "tls": tls,
                "keys": [{
                    "keyId": "%s.%s" % (app_id, k.get("id", "")),
                    "keyValue": k.get("value", ""),
                    "key_str": "%s.%s:%s" % (app_id,  k.get("id", ""), k.get("value", "")),
                    "capability" : k.get("capability")
                } for k in app_spec.get("keys", [])]
            }

            RestSetup.__test_vars = test_vars
        return RestSetup.__test_vars

    @staticmethod
    def clear_test_vars():
        test_vars = RestSetup.__test_vars
        options = Options.with_key(test_vars["keys"][0]["key_str"], restHost=host, port=port,tls_port=port,tls=tls)
        ably = AblyRest(options)
        headers = HttpUtils.default_get_headers()
        RestSetup.__test_vars = None
