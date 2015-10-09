from __future__ import absolute_import

import logging
import time
import unittest
import base64

import mock
import six
from requests import Session

from ably import AblyRest
from ably import Auth
from ably import Options
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase, VaryByProtocolTestsMetaclass, dont_vary_protocol 

test_vars = RestSetup.get_test_vars()


log = logging.getLogger(__name__)


# does not make any request, no need to vary by protocol
class TestAuth(BaseTestCase):

    def test_auth_init_key_only(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"])
        self.assertEqual(Auth.Method.BASIC, ably.auth.auth_method,
                         msg="Unexpected Auth method mismatch")

    def test_auth_init_token_only(self):
        ably = AblyRest(token="this_is_not_really_a_token")

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                         msg="Unexpected Auth method mismatch")

    def test_auth_token_details(self):
        td = TokenDetails()
        ably = AblyRest(token_details=td)

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method)
        self.assertIs(ably.auth.token_details, td)

    def test_auth_init_with_token_callback(self):
        callback_called = []

        def token_callback(**params):
            callback_called.append(True)
            return "this_is_not_really_a_token_request"

        ably = AblyRest(key_name=test_vars["keys"][0]["key_name"],
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        auth_callback= token_callback)

        try:
            ably.stats(None)
        except:
            pass

        self.assertTrue(callback_called, msg="Token callback not called")
        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_key_and_client_id(self):
        ably = AblyRest(key=test_vars["keys"][0]["key_str"], client_id='testClientId')

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_auth_init_with_token(self):

        ably = AblyRest(token="this_is_not_really_a_token",
                        rest_host=test_vars["host"],
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"])

        self.assertEqual(Auth.Method.TOKEN, ably.auth.auth_method,
                msg="Unexpected Auth method mismatch")

    def test_request_basic_auth_header(self):
        ably = AblyRest(key_secret='foo', key_name='bar')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        self.assertEqual(authorization,
                         'Basic %s' %
                         base64.b64encode('bar:foo'.encode('ascii')
                                          ).decode('utf-8'))

    def test_request_token_auth_header(self):
        ably = AblyRest(token='not_a_real_token')

        with mock.patch.object(Session, 'prepare_request') as get_mock:
            try:
                ably.http.get('/time', skip_auth=False)
            except Exception:
                pass
        request = get_mock.call_args_list[0][0][0]
        authorization = request.headers['Authorization']
        self.assertEqual(authorization,
                         'Bearer %s' %
                         base64.b64encode('not_a_real_token'.encode('ascii')
                                          ).decode('utf-8'))

    def test_if_cant_authenticate_via_token(self):
        self.assertRaises(ValueError, AblyRest, use_token_auth=True)

    def test_use_auth_token(self):
        ably = AblyRest(use_token_auth=True, key=test_vars["keys"][0]["key_str"])
        self.assertEquals(ably.auth.auth_method, Auth.Method.TOKEN)

    def test_with_client_id(self):
        ably = AblyRest(client_id='client_id', key=test_vars["keys"][0]["key_str"])
        self.assertEquals(ably.auth.auth_method, Auth.Method.TOKEN)

    def test_with_auth_url(self):
        ably = AblyRest(auth_url='auth_url')
        self.assertEquals(ably.auth.auth_method, Auth.Method.TOKEN)

    def test_with_auth_callback(self):
        ably = AblyRest(auth_callback=lambda x: x)
        self.assertEquals(ably.auth.auth_method, Auth.Method.TOKEN)

    def test_with_token(self):
        ably = AblyRest(token='a token')
        self.assertEquals(ably.auth.auth_method, Auth.Method.TOKEN)

    def test_default_ttl_is_1hour(self):
        one_hour_in_seconds = 60 * 60
        self.assertEquals(TokenDetails.DEFAULTS['ttl'], one_hour_in_seconds)


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestAuthAuthorize(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_if_authorize_changes_auth_method_to_token(self):

        self.assertEqual(Auth.Method.BASIC, self.ably.auth.auth_method,
                         msg="Unexpected Auth method mismatch")

        self.ably.auth.authorise()

        self.assertEqual(Auth.Method.TOKEN, self.ably.auth.auth_method,
                         msg="Authorise should change the Auth method")

    def test_authorize_shouldnt_create_token_if_not_expired(self):

        token = self.ably.auth.authorise()

        new_token = self.ably.auth.authorise()

        self.assertGreater(token.expires, time.time()*1000)

        self.assertIs(new_token, token)

    def test_authorize_should_create_new_token_if_forced(self):

        token = self.ably.auth.authorise()

        new_token = self.ably.auth.authorise(force=True)

        self.assertGreater(token.expires, time.time()*1000)

        self.assertIsNot(new_token, token)
        self.assertGreater(new_token.expires, token.expires)

    def test_authorize_create_new_token_if_expired(self):

        token = self.ably.auth.authorise()

        with mock.patch('ably.types.tokendetails.TokenDetails.expires',
                        new_callable=mock.PropertyMock(return_value=42)):
            new_token = self.ably.auth.authorise()

        self.assertIsNot(token, new_token)

    def test_authorize_returns_a_token_details(self):

        token = self.ably.auth.authorise()

        self.assertIsInstance(token, TokenDetails)

    @dont_vary_protocol
    def test_authorize_adhere_to_request_token(self):

        token_params = {'ttl': 100}
        auth_params = {'auth_url': 'http://somewhere.com'}

        with mock.patch('ably.rest.auth.Auth.request_token') as request_mock:
            self.ably.auth.authorise(auth_params=auth_params,
                                     token_params=token_params)

        request_mock.assert_called_once_with(auth_params=auth_params,
                                             token_params=token_params)

    def test_with_token_str_https(self):
        token = self.ably.auth.authorise()
        token = token.token
        ably = AblyRest(token=token, rest_host=test_vars["host"],
                        port=test_vars["port"], tls_port=test_vars["tls_port"],
                        tls=True, use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')

    def test_with_token_str_http(self):
        token = self.ably.auth.authorise()
        token = token.token
        ably = AblyRest(token=token, rest_host=test_vars["host"],
                        port=test_vars["port"], tls_port=test_vars["tls_port"],
                        tls=False, use_binary_protocol=self.use_binary_protocol)
        ably.channels.test_auth_with_token_str.publish('event', 'foo_bar')
