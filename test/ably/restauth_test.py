from __future__ import absolute_import

import logging
import unittest
import responses
import mock

from os.path import join, abspath, dirname, normpath

from ably import AblyRest
from ably import Auth
from ably import Options
from ably.util.exceptions import AblyException

log = logging.getLogger(__name__)


class TestAuth(unittest.TestCase):

    def _add_stats_responses(self):
        with open(normpath(join(abspath(dirname(__file__)), '..', 'api_responses', 'stats.json'))) as f:
            body = f.read()
        responses.add(
            responses.GET, 'https://rest.ably.io:443/stats',
            body=body, status=200,
            content_type='application/json',
            adding_headers={
                'access-control-expose-headers': 'Link',
                'vary': 'Origin', 'connection': 'keep-alive',
                'link': '<./stats?start=0&end=1431454230723&limit=100&unit=minute&'
                        'direction=backwards&format=json&first_end=1431454230723>; rel="first", '
                        '<./stats?start=0&end=1431454230723&limit=100&unit=minute&'
                        'direction=backwards&format=json&first_end=1431454230723>; rel="current"',
                'access-control-allow-credentials': 'true',
                'date': 'Tue, 12 May 2015 18:10:30 GMT',
                'access-control-allow-origin': '*'
            })
        responses.add(
            responses.POST, 'https://rest.ably.io:443/keys/mykey.myvalue/requestToken',
            body='{"error": {"statusCode": 401, "code": 40101, "message": "No keyName specified" }}',
            status=401, content_type='application/json',
            adding_headers={
                'access-control-expose-headers': 'Link',
                'vary': 'Origin', 'connection': 'keep-alive',
                'access-control-allow-credentials': 'true',
                'date': 'Tue, 12 May 2015 18:10:30 GMT',
                'access-control-allow-origin': '*'
            })

    def test_auth_init_key_only(self):

        ably = AblyRest(Options.with_key('mykey.myvalue:mySecRet'))
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
            msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        ably = AblyRest(Options(auth_token="this_is_not_really_a_token"))
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
            msg="Unexpected Auth method mismatch")

    @responses.activate
    def test_auth_init_with_token_callback(self):
        options = Options(key_id='mykey.myvalue')
        options.auth_callback = mock.MagicMock()
        self._add_stats_responses()

        ably = AblyRest(options)
        try:
            ably.stats(None)
        except AblyException:
            pass

        options.auth_callback.assert_called_once_with(client_id=None)
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_key_and_client_id(self):
        options = Options.with_key('mykey.myvalue:mySecRet')
        options.client_id = "testClientId"

        ably = AblyRest(options)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):
        options = Options(host='example.com', port=80, tls_port=123, tls='tls.example.com')

        ably = AblyRest(options)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")
