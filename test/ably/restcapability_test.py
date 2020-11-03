import pytest

from ably.types.capability import Capability
from ably.util.exceptions import AblyException

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseTestCase

test_vars = RestSetup.get_test_vars()


class TestRestCapability(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):
    @classmethod
    def setUpClass(cls):
        cls.ably = RestSetup.get_ably_rest()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol

    def test_blanket_intersection_with_key(self):
        key = test_vars['keys'][1]
        token_details = self.ably.auth.request_token(key_name=key['key_name'],
                                                     key_secret=key['key_secret'])
        expected_capability = Capability(key["capability"])
        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability."

    def test_equal_intersection_with_key(self):
        key = test_vars['keys'][1]

        token_details = self.ably.auth.request_token(
            key_name=key['key_name'],
            key_secret=key['key_secret'],
            token_params={'capability': key['capability']})

        expected_capability = Capability(key["capability"])

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    @dont_vary_protocol
    def test_empty_ops_intersection(self):
        key = test_vars['keys'][1]
        with pytest.raises(AblyException):
            self.ably.auth.request_token(
                key_name=key['key_name'],
                key_secret=key['key_secret'],
                token_params={'capability': {'testchannel': ['subscribe']}})

    @dont_vary_protocol
    def test_empty_paths_intersection(self):
        key = test_vars['keys'][1]
        with pytest.raises(AblyException):
            self.ably.auth.request_token(
                key_name=key['key_name'],
                key_secret=key['key_secret'],
                token_params={'capability': {"testchannelx": ["publish"]}})

    def test_non_empty_ops_intersection(self):
        key = test_vars['keys'][4]

        token_params = {"capability": {
            "channel2": ["presence", "subscribe"]
        }}
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],
        }

        expected_capability = Capability({
            "channel2": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_non_empty_paths_intersection(self):
        key = test_vars['keys'][4]
        token_params = {
            "capability": {
                "channel2": ["presence", "subscribe"],
                "channelx": ["presence", "subscribe"],
            }
        }
        kwargs = {
            "key_name": key["key_name"],

            "key_secret": key["key_secret"]
        }

        expected_capability = Capability({
            "channel2": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_wildcard_ops_intersection(self):
        key = test_vars['keys'][4]

        token_params = {
            "capability": {
                "channel2": ["*"],
            },
        }
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],
        }

        expected_capability = Capability({
            "channel2": ["subscribe", "publish"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_wildcard_ops_intersection_2(self):
        key = test_vars['keys'][4]

        token_params = {
            "capability": {
                "channel6": ["publish", "subscribe"],
            },
        }
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],
        }

        expected_capability = Capability({
            "channel6": ["subscribe", "publish"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_wildcard_resources_intersection(self):
        key = test_vars['keys'][2]

        token_params = {
            "capability": {
                "cansubscribe": ["subscribe"],
            },
        }
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],
        }

        expected_capability = Capability({
            "cansubscribe": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_wildcard_resources_intersection_2(self):
        key = test_vars['keys'][2]

        token_params = {
            "capability": {
                "cansubscribe:check": ["subscribe"],
            },
        }
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],
        }

        expected_capability = Capability({
            "cansubscribe:check": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    def test_wildcard_resources_intersection_3(self):
        key = test_vars['keys'][2]

        token_params = {
            "capability": {
                "cansubscribe:*": ["subscribe"],
            },
        }
        kwargs = {
            "key_name": key["key_name"],
            "key_secret": key["key_secret"],

        }

        expected_capability = Capability({
            "cansubscribe:*": ["subscribe"]
        })

        token_details = self.ably.auth.request_token(token_params, **kwargs)

        assert token_details.token is not None, "Expected token"
        assert expected_capability == token_details.capability, "Unexpected capability"

    @dont_vary_protocol
    def test_invalid_capabilities(self):
        with pytest.raises(AblyException) as excinfo:
            self.ably.auth.request_token(
                token_params={'capability': {"channel0": ["publish_"]}})

        the_exception = excinfo.value
        assert 400 == the_exception.status_code
        assert 40000 == the_exception.code

    @dont_vary_protocol
    def test_invalid_capabilities_2(self):
        with pytest.raises(AblyException) as excinfo:
            self.ably.auth.request_token(
                token_params={'capability': {"channel0": ["*", "publish"]}})

        the_exception = excinfo.value
        assert 400 == the_exception.status_code
        assert 40000 == the_exception.code

    @dont_vary_protocol
    def test_invalid_capabilities_3(self):
        with pytest.raises(AblyException) as excinfo:
            self.ably.auth.request_token(
                token_params={'capability': {"channel0": []}})

        the_exception = excinfo.value
        assert 400 == the_exception.status_code
        assert 40000 == the_exception.code
