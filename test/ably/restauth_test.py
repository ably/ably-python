from __future__ import absolute_import

import logging
import time
import unittest

import mock
import six

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
        options = Options(key=test_vars["keys"][0]["key_str"])

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
