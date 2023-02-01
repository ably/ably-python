import warnings
from mock import patch
import pytest
from httpx import AsyncClient

from ably import AblyRest
from ably import AblyException
from ably.transport.defaults import Defaults
from ably.types.tokendetails import TokenDetails

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol, BaseAsyncTestCase


class TestRestInit(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def asyncSetUp(self):
        self.test_vars = await RestSetup.get_test_vars()

    @dont_vary_protocol
    def test_key_only(self):
        ably = AblyRest(key=self.test_vars["keys"][0]["key_str"])
        assert ably.options.key_name == self.test_vars["keys"][0]["key_name"], "Key name does not match"
        assert ably.options.key_secret == self.test_vars["keys"][0]["key_secret"], "Key secret does not match"

    def per_protocol_setup(self, use_binary_protocol):
        self.use_binary_protocol = use_binary_protocol

    @dont_vary_protocol
    def test_with_token(self):
        ably = AblyRest(token="foo")
        assert ably.options.auth_token == "foo", "Token not set at options"

    @dont_vary_protocol
    def test_with_token_details(self):
        td = TokenDetails()
        ably = AblyRest(token_details=td)
        assert ably.options.token_details is td

    @dont_vary_protocol
    def test_with_options_token_callback(self):
        def token_callback(**params):
            return "this_is_not_really_a_token_request"
        AblyRest(auth_callback=token_callback)

    @dont_vary_protocol
    def test_ambiguous_key_raises_value_error(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            AblyRest(key=self.test_vars["keys"][0]["key_str"], key_name='x')
        with pytest.raises(ValueError, match="mutually exclusive"):
            AblyRest(key=self.test_vars["keys"][0]["key_str"], key_secret='x')

    @dont_vary_protocol
    def test_with_key_name_or_secret_only(self):
        with pytest.raises(ValueError, match="key is missing"):
            AblyRest(key_name='x')
        with pytest.raises(ValueError, match="key is missing"):
            AblyRest(key_secret='x')

    @dont_vary_protocol
    def test_with_key_name_and_secret(self):
        ably = AblyRest(key_name="foo", key_secret="bar")
        assert ably.options.key_name == "foo", "Key name does not match"
        assert ably.options.key_secret == "bar", "Key secret does not match"

    @dont_vary_protocol
    def test_with_options_auth_url(self):
        AblyRest(auth_url='not_really_an_url')

    # RSC11
    @dont_vary_protocol
    def test_rest_host_and_environment(self):
        # rest host
        ably = AblyRest(token='foo', rest_host="some.other.host")
        assert "some.other.host" == ably.options.rest_host, "Unexpected host mismatch"

        # environment: production
        ably = AblyRest(token='foo', environment="production")
        host = ably.options.get_rest_host()
        assert "rest.ably.io" == host, "Unexpected host mismatch %s" % host

        # environment: other
        ably = AblyRest(token='foo', environment="sandbox")
        host = ably.options.get_rest_host()
        assert "sandbox-rest.ably.io" == host, "Unexpected host mismatch %s" % host

        # both, as per #TO3k2
        with pytest.raises(ValueError):
            ably = AblyRest(token='foo', rest_host="some.other.host",
                            environment="some.other.environment")

    # RSC15
    @dont_vary_protocol
    # Ignore library warning regarding fallback_hosts_use_default
    @pytest.mark.filterwarnings('ignore::DeprecationWarning')
    def test_fallback_hosts(self):
        # Specify the fallback_hosts (RSC15a)
        fallback_hosts = [
            ['fallback1.com', 'fallback2.com'],
            [],
        ]

        # Fallback hosts specified (RSC15g1)
        for aux in fallback_hosts:
            ably = AblyRest(token='foo', fallback_hosts=aux)
            assert sorted(aux) == sorted(ably.options.get_fallback_rest_hosts())

        # Specify environment (RSC15g2)
        ably = AblyRest(token='foo', environment='sandbox', http_max_retry_count=10)
        assert sorted(Defaults.get_environment_fallback_hosts('sandbox')) == sorted(
            ably.options.get_fallback_rest_hosts())

        # Fallback hosts and environment not specified (RSC15g3)
        ably = AblyRest(token='foo', http_max_retry_count=10)
        assert sorted(Defaults.fallback_hosts) == sorted(ably.options.get_fallback_rest_hosts())

        # Specify environment and fallback_hosts_use_default, no fallback hosts (RSC15g4)
        # We specify http_max_retry_count=10 so all the fallback hosts get in the list
        ably = AblyRest(token='foo', environment='not_considered', fallback_hosts_use_default=True,
                        http_max_retry_count=10)
        assert sorted(Defaults.fallback_hosts) == sorted(ably.options.get_fallback_rest_hosts())

        # RSC15f
        ably = AblyRest(token='foo')
        assert 600000 == ably.options.fallback_retry_timeout
        ably = AblyRest(token='foo', fallback_retry_timeout=1000)
        assert 1000 == ably.options.fallback_retry_timeout

        with warnings.catch_warnings(record=True) as ws:
            # Cause all warnings to always be triggered
            warnings.simplefilter("always")
            AblyRest(token='foo', fallback_hosts_use_default=True)
            # Verify warning is raised for fallback_hosts_use_default
            ws = [w for w in ws if issubclass(w.category, DeprecationWarning)]
            assert len(ws) == 1

    @dont_vary_protocol
    def test_specified_realtime_host(self):
        ably = AblyRest(token='foo', realtime_host="some.other.host")
        assert "some.other.host" == ably.options.realtime_host, "Unexpected host mismatch"

    @dont_vary_protocol
    def test_specified_port(self):
        ably = AblyRest(token='foo', port=9998, tls_port=9999)
        assert 9999 == Defaults.get_port(ably.options),\
               "Unexpected port mismatch. Expected: 9999. Actual: %d" % ably.options.tls_port

    @dont_vary_protocol
    def test_specified_non_tls_port(self):
        ably = AblyRest(token='foo', port=9998, tls=False)
        assert 9998 == Defaults.get_port(ably.options),\
               "Unexpected port mismatch. Expected: 9999. Actual: %d" % ably.options.tls_port

    @dont_vary_protocol
    def test_specified_tls_port(self):
        ably = AblyRest(token='foo', tls_port=9999, tls=True)
        assert 9999 == Defaults.get_port(ably.options),\
               "Unexpected port mismatch. Expected: 9999. Actual: %d" % ably.options.tls_port

    @dont_vary_protocol
    def test_tls_defaults_to_true(self):
        ably = AblyRest(token='foo')
        assert ably.options.tls, "Expected encryption to default to true"
        assert Defaults.tls_port == Defaults.get_port(ably.options), "Unexpected port mismatch"

    @dont_vary_protocol
    def test_tls_can_be_disabled(self):
        ably = AblyRest(token='foo', tls=False)
        assert not ably.options.tls, "Expected encryption to be False"
        assert Defaults.port == Defaults.get_port(ably.options), "Unexpected port mismatch"

    @dont_vary_protocol
    def test_with_no_params(self):
        with pytest.raises(ValueError):
            AblyRest()

    @dont_vary_protocol
    def test_with_no_auth_params(self):
        with pytest.raises(ValueError):
            AblyRest(port=111)

    # RSA10k
    async def test_query_time_param(self):
        ably = await RestSetup.get_ably_rest(query_time=True,
                                             use_binary_protocol=self.use_binary_protocol)

        timestamp = ably.auth._timestamp
        with patch('ably.rest.rest.AblyRest.time', wraps=ably.time) as server_time,\
                patch('ably.rest.auth.Auth._timestamp', wraps=timestamp) as local_time:
            await ably.auth.request_token()
            assert local_time.call_count == 1
            assert server_time.call_count == 1
            await ably.auth.request_token()
            assert local_time.call_count == 2
            assert server_time.call_count == 1

        await ably.close()

    @dont_vary_protocol
    def test_requests_over_https_production(self):
        ably = AblyRest(token='token')
        assert 'https://rest.ably.io' == '{0}://{1}'.format(ably.http.preferred_scheme, ably.http.preferred_host)
        assert ably.http.preferred_port == 443

    @dont_vary_protocol
    def test_requests_over_http_production(self):
        ably = AblyRest(token='token', tls=False)
        assert 'http://rest.ably.io' == '{0}://{1}'.format(ably.http.preferred_scheme, ably.http.preferred_host)
        assert ably.http.preferred_port == 80

    @dont_vary_protocol
    async def test_request_basic_auth_over_http_fails(self):
        ably = AblyRest(key_secret='foo', key_name='bar', tls=False)

        with pytest.raises(AblyException) as excinfo:
            await ably.http.get('/time', skip_auth=False)

        assert 401 == excinfo.value.status_code
        assert 40103 == excinfo.value.code
        assert 'Cannot use Basic Auth over non-TLS connections' == excinfo.value.message

    @dont_vary_protocol
    async def test_environment(self):
        ably = AblyRest(token='token', environment='custom')
        with patch.object(AsyncClient, 'send', wraps=ably.http._Http__client.send) as get_mock:
            try:
                await ably.time()
            except AblyException:
                pass
            request = get_mock.call_args_list[0][0][0]
            assert request.url == 'https://custom-rest.ably.io:443/time'

        await ably.close()

    @dont_vary_protocol
    def test_accepts_custom_http_timeouts(self):
        ably = AblyRest(
            token="foo", http_request_timeout=30, http_open_timeout=8,
            http_max_retry_count=6, http_max_retry_duration=20)

        assert ably.options.http_request_timeout == 30
        assert ably.options.http_open_timeout == 8
        assert ably.options.http_max_retry_count == 6
        assert ably.options.http_max_retry_duration == 20
