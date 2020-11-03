import datetime
import json
import logging

from mock import patch
import pytest

from ably import AblyException
from ably import AblyRest
from ably import Capability
from ably.types.tokendetails import TokenDetails
from ably.types.tokenrequest import TokenRequest

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

log = logging.getLogger(__name__)


class TestRestToken(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def server_time(self):
        return self.ably.time()

    def setUp(self):
        capability = {"*": ["*"]}
        self.permit_all = str(Capability(capability))
        self.ably = RestSetup.get_ably_rest()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_request_token_null_params(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token()
        post_time = self.server_time()
        assert token_details.token is not None, "Expected token"
        assert token_details.issued >= pre_time, "Unexpected issued time"
        assert token_details.issued <= post_time, "Unexpected issued time"
        assert self.permit_all == str(token_details.capability), "Unexpected capability"

    def test_request_token_explicit_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(token_params={'timestamp': pre_time})
        post_time = self.server_time()
        assert token_details.token is not None, "Expected token"
        assert token_details.issued >= pre_time, "Unexpected issued time"
        assert token_details.issued <= post_time, "Unexpected issued time"
        assert self.permit_all == str(Capability(token_details.capability)), "Unexpected Capability"

    def test_request_token_explicit_invalid_timestamp(self):
        request_time = self.server_time()
        explicit_timestamp = request_time - 30 * 60 * 1000

        with pytest.raises(AblyException):
            self.ably.auth.request_token(token_params={'timestamp': explicit_timestamp})

    def test_request_token_with_system_timestamp(self):
        pre_time = self.server_time()
        token_details = self.ably.auth.request_token(query_time=True)
        post_time = self.server_time()
        assert token_details.token is not None, "Expected token"
        assert token_details.issued >= pre_time, "Unexpected issued time"
        assert token_details.issued <= post_time, "Unexpected issued time"
        assert self.permit_all == str(Capability(token_details.capability)), "Unexpected Capability"

    def test_request_token_with_duplicate_nonce(self):
        request_time = self.server_time()
        token_params = {
            'timestamp': request_time,
            'nonce': '1234567890123456'
        }
        token_details = self.ably.auth.request_token(token_params)
        assert token_details.token is not None, "Expected token"

        with pytest.raises(AblyException):
            self.ably.auth.request_token(token_params)

    def test_request_token_with_capability_that_subsets_key_capability(self):
        capability = Capability({
            "onlythischannel": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(
            token_params={'capability': capability})

        assert token_details is not None
        assert token_details.token is not None
        assert capability == token_details.capability, "Unexpected capability"

    def test_request_token_with_specified_key(self):
        key = RestSetup.get_test_vars()["keys"][1]
        token_details = self.ably.auth.request_token(
            key_name=key["key_name"], key_secret=key["key_secret"])
        assert token_details.token is not None, "Expected token"
        assert key.get("capability") == token_details.capability, "Unexpected capability"

    @dont_vary_protocol
    def test_request_token_with_invalid_mac(self):
        with pytest.raises(AblyException):
            self.ably.auth.request_token(token_params={'mac': "thisisnotavalidmac"})

    def test_request_token_with_specified_ttl(self):
        token_details = self.ably.auth.request_token(token_params={'ttl': 100})
        assert token_details.token is not None, "Expected token"
        assert token_details.issued + 100 == token_details.expires, "Unexpected expires"

    @dont_vary_protocol
    def test_token_with_excessive_ttl(self):
        excessive_ttl = 365 * 24 * 60 * 60 * 1000
        with pytest.raises(AblyException):
            self.ably.auth.request_token(token_params={'ttl': excessive_ttl})

    @dont_vary_protocol
    def test_token_generation_with_invalid_ttl(self):
        with pytest.raises(AblyException):
            self.ably.auth.request_token(token_params={'ttl': -1})

    def test_token_generation_with_local_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token()
            assert local_time.called
            assert not server_time.called

    # RSA10k
    def test_token_generation_with_server_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.request_token(query_time=True)
            assert local_time.call_count == 1
            assert server_time.call_count == 1
            self.ably.auth.request_token(query_time=True)
            assert local_time.call_count == 2
            assert server_time.call_count == 1

    # TD7
    def test_toke_details_from_json(self):
        token_details = self.ably.auth.request_token()
        token_details_dict = token_details.to_dict()
        token_details_str = json.dumps(token_details_dict)

        assert token_details == TokenDetails.from_json(token_details_dict)
        assert token_details == TokenDetails.from_json(token_details_str)

    # Issue #71
    @dont_vary_protocol
    def test_request_token_float_and_timedelta(self):
        lifetime = datetime.timedelta(hours=4)
        self.ably.auth.request_token({'ttl': lifetime.total_seconds() * 1000})
        self.ably.auth.request_token({'ttl': lifetime})


class TestCreateTokenRequest(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def setUp(self):
        self.ably = RestSetup.get_ably_rest()
        self.key_name = self.ably.options.key_name
        self.key_secret = self.ably.options.key_secret

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    @dont_vary_protocol
    def test_key_name_and_secret_are_required(self):
        ably = RestSetup.get_ably_rest(key=None, token='not a real token')
        with pytest.raises(AblyException, match="40101 401 No key specified"):
            ably.auth.create_token_request()
        with pytest.raises(AblyException, match="40101 401 No key specified"):
            ably.auth.create_token_request(key_name=self.key_name)
        with pytest.raises(AblyException, match="40101 401 No key specified"):
            ably.auth.create_token_request(key_secret=self.key_secret)

    @dont_vary_protocol
    def test_with_local_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.create_token_request(
                key_name=self.key_name, key_secret=self.key_secret, query_time=False)
            assert local_time.called
            assert not server_time.called

    # RSA10k
    @dont_vary_protocol
    def test_with_server_time(self):
        timestamp = self.ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=self.ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            self.ably.auth.create_token_request(
                key_name=self.key_name, key_secret=self.key_secret, query_time=True)
            assert local_time.call_count == 1
            assert server_time.call_count == 1
            self.ably.auth.create_token_request(
                key_name=self.key_name, key_secret=self.key_secret, query_time=True)
            assert local_time.call_count == 2
            assert server_time.call_count == 1

    def test_token_request_can_be_used_to_get_a_token(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert isinstance(token_request, TokenRequest)

        ably = RestSetup.get_ably_rest(key=None,
                                       auth_callback=lambda x: token_request,
                                       use_binary_protocol=self.use_binary_protocol)

        token = ably.auth.authorize()
        assert isinstance(token, TokenDetails)

    def test_token_request_dict_can_be_used_to_get_a_token(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert isinstance(token_request, TokenRequest)

        ably = RestSetup.get_ably_rest(key=None,
                                       auth_callback=lambda x: token_request.to_dict(),
                                       use_binary_protocol=self.use_binary_protocol)

        token = ably.auth.authorize()
        assert isinstance(token, TokenDetails)

    # TE6
    @dont_vary_protocol
    def test_token_request_from_json(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert isinstance(token_request, TokenRequest)

        token_request_dict = token_request.to_dict()
        assert token_request == TokenRequest.from_json(token_request_dict)

        token_request_str = json.dumps(token_request_dict)
        assert token_request == TokenRequest.from_json(token_request_str)

    @dont_vary_protocol
    def test_nonce_is_random_and_longer_than_15_characters(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert len(token_request.nonce) > 15

        another_token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert len(another_token_request.nonce) > 15

        assert token_request.nonce != another_token_request.nonce

    # RSA5
    @dont_vary_protocol
    def test_ttl_is_optional_and_specified_in_ms(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert token_request.ttl is None

    # RSA6
    @dont_vary_protocol
    def test_capability_is_optional(self):
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret)
        assert token_request.capability is None

    @dont_vary_protocol
    def test_accept_all_token_params(self):
        token_params = {
            'ttl': 1000,
            'capability': Capability({'channel': ['publish']}),
            'client_id': 'a_id',
            'timestamp': 1000,
            'nonce': 'a_nonce',
        }
        token_request = self.ably.auth.create_token_request(
            token_params,
            key_name=self.key_name, key_secret=self.key_secret,
        )
        assert token_request.ttl == token_params['ttl']
        assert token_request.capability == str(token_params['capability'])
        assert token_request.client_id == token_params['client_id']
        assert token_request.timestamp == token_params['timestamp']
        assert token_request.nonce == token_params['nonce']

    def test_capability(self):
        capability = Capability({'channel': ['publish']})
        token_request = self.ably.auth.create_token_request(
            key_name=self.key_name, key_secret=self.key_secret,
            token_params={'capability': capability})
        assert token_request.capability == str(capability)

        def auth_callback(token_params):
            return token_request

        ably = RestSetup.get_ably_rest(key=None, auth_callback=auth_callback,
                                       use_binary_protocol=self.use_binary_protocol)

        token = ably.auth.authorize()

        assert str(token.capability) == str(capability)

    @dont_vary_protocol
    def test_hmac(self):
        ably = AblyRest(key_name='a_key_name', key_secret='a_secret')
        token_params = {
            'ttl': 1000,
            'nonce': 'abcde100',
            'client_id': 'a_id',
            'timestamp': 1000,
        }
        token_request = ably.auth.create_token_request(
            token_params, key_secret='a_secret', key_name='a_key_name')
        assert token_request.mac == 'sYkCH0Un+WgzI7/Nhy0BoQIKq9HmjKynCRs4E3qAbGQ='
