import json
import os
import logging

from ably.rest.rest import AblyRest
from ably.types.capability import Capability
from ably.types.options import Options
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)

app_spec_local = None
with open(os.path.dirname(__file__) + '/../assets/testAppSpec.json', 'r') as f:
    app_spec_local = json.loads(f.read())

tls = (os.environ.get('ABLY_TLS') or "true").lower() == "true"
host = os.environ.get('ABLY_HOST', 'sandbox-rest.ably.io')
environment = os.environ.get('ABLY_ENV')

port = 80
tls_port = 443

if host and not host.endswith("rest.ably.io"):
    tls = tls and not host.equals("localhost")
    port = 8080
    tls_port = 8081


ably = AblyRest(token='not_a_real_token', rest_host=host,
                port=port, tls_port=tls_port, tls=tls,
                environment=environment,
                use_binary_protocol=False)


class RestSetup:
    __test_vars = None

    @staticmethod
    def get_test_vars(sender=None):
        if not RestSetup.__test_vars:
            r = ably.http.post("/apps", body=app_spec_local, skip_auth=True)
            AblyException.raise_for_response(r)

            app_spec = r.json()

            app_id = app_spec.get("appId", "")

            test_vars = {
                "app_id": app_id,
                "host": host,
                "port": port,
                "tls_port": tls_port,
                "tls": tls,
                "environment": environment,
                "keys": [{
                    "key_name": "%s.%s" % (app_id, k.get("id", "")),
                    "key_secret": k.get("value", ""),
                    "key_str": "%s.%s:%s" % (app_id, k.get("id", ""), k.get("value", "")),
                    "capability": Capability(json.loads(k.get("capability", "{}"))),
                } for k in app_spec.get("keys", [])]
            }

            RestSetup.__test_vars = test_vars
            log.debug([(app_id, k.get("id", ""), k.get("value", ""))
                  for k in app_spec.get("keys", [])])
        return RestSetup.__test_vars

    @classmethod
    def get_ably_rest(cls, **kw):
        test_vars = RestSetup.get_test_vars()
        options = {
            'key': test_vars["keys"][0]["key_str"],
            'rest_host': test_vars["host"],
            'port': test_vars["port"],
            'tls_port': test_vars["tls_port"],
            'tls': test_vars["tls"],
            'environment': test_vars["environment"],
        }
        options.update(kw)
        return AblyRest(**options)

    @classmethod
    def clear_test_vars(cls):
        test_vars = RestSetup.__test_vars
        options = Options(key=test_vars["keys"][0]["key_str"])
        options.rest_host = test_vars["host"]
        options.port = test_vars["port"]
        options.tls_port = test_vars["tls_port"]
        options.tls = test_vars["tls"]
        ably = cls.get_ably_rest()
        ably.http.delete('/apps/' + test_vars['app_id'])
        RestSetup.__test_vars = None
