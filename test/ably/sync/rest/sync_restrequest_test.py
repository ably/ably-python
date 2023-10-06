import httpx
import pytest
import respx

from ably.sync import AblyRestSync
from ably.sync.http.paginatedresult import HttpPaginatedResponseSync
from ably.sync.transport.defaults import Defaults
from test.ably.sync.testapp import TestApp
from test.ably.sync.utils import BaseAsyncTestCase
from test.ably.sync.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol


# RSC19
class TestRestRequest(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    def setUp(self):
        self.ably = TestApp.get_ably_rest()
        self.test_vars = TestApp.get_test_vars()

        # Populate the channel (using the new api)
        self.channel = self.get_channel_name()
        self.path = '/channels/%s/messages' % self.channel
        for i in range(20):
            body = {'name': 'event%s' % i, 'data': 'lorem ipsum %s' % i}
            self.ably.request('POST', self.path, body=body, version=Defaults.protocol_version)

    def tearDown(self):
        self.ably.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_post(self):
        body = {'name': 'test-post', 'data': 'lorem ipsum'}
        result = self.ably.request('POST', self.path, body=body, version=Defaults.protocol_version)

        assert isinstance(result, HttpPaginatedResponseSync)  # RSC19d
        # HP3
        assert type(result.items) is list
        assert len(result.items) == 1
        assert result.items[0]['channel'] == self.channel
        assert 'messageId' in result.items[0]

    def test_get(self):
        params = {'limit': 10, 'direction': 'forwards'}
        result = self.ably.request('GET', self.path, params=params, version=Defaults.protocol_version)

        assert isinstance(result, HttpPaginatedResponseSync)  # RSC19d

        # HP2
        assert isinstance(result.next(), HttpPaginatedResponseSync)
        assert isinstance(result.first(), HttpPaginatedResponseSync)

        # HP3
        assert isinstance(result.items, list)
        item = result.items[0]
        assert isinstance(item, dict)
        assert 'timestamp' in item
        assert 'id' in item
        assert item['name'] == 'event0'
        assert item['data'] == 'lorem ipsum 0'

        assert result.status_code == 200     # HP4
        assert result.success is True        # HP5
        assert result.error_code is None     # HP6
        assert result.error_message is None  # HP7
        assert isinstance(result.headers, list)   # HP7

    @dont_vary_protocol
    def test_not_found(self):
        result = self.ably.request('GET', '/not-found', version=Defaults.protocol_version)
        assert isinstance(result, HttpPaginatedResponseSync)  # RSC19d
        assert result.status_code == 404             # HP4
        assert result.success is False               # HP5

    @dont_vary_protocol
    def test_error(self):
        params = {'limit': 'abc'}
        result = self.ably.request('GET', self.path, params=params, version=Defaults.protocol_version)
        assert isinstance(result, HttpPaginatedResponseSync)  # RSC19d
        assert result.status_code == 400  # HP4
        assert not result.success
        assert result.error_code
        assert result.error_message

    def test_headers(self):
        key = 'X-Test'
        value = 'lorem ipsum'
        result = self.ably.request('GET', '/time', headers={key: value}, version=Defaults.protocol_version)
        assert result.response.request.headers[key] == value

    # RSC19e
    @dont_vary_protocol
    def test_timeout(self):
        # Timeout
        timeout = 0.000001
        ably = AblyRestSync(token="foo", http_request_timeout=timeout)
        assert ably.http.http_request_timeout == timeout
        with pytest.raises(httpx.ReadTimeout):
            ably.request('GET', '/time', version=Defaults.protocol_version)
        ably.close()

        default_endpoint = 'https://sandbox-rest.ably.io/time'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/time'
        ably = TestApp.get_ably_rest(fallback_hosts=[fallback_host])
        with respx.mock:
            default_route = respx.get(default_endpoint)
            fallback_route = respx.get(fallback_endpoint)
            headers = {
                "Content-Type": "application/json"
            }
            default_route.side_effect = httpx.ConnectError('')
            fallback_route.return_value = httpx.Response(200, headers=headers, text='[123]')
            ably.request('GET', '/time', version=Defaults.protocol_version)
        ably.close()

        # Bad host, no Fallback
        ably = AblyRestSync(key=self.test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=self.test_vars["port"],
                        tls_port=self.test_vars["tls_port"],
                        tls=self.test_vars["tls"])
        with pytest.raises(httpx.ConnectError):
            ably.request('GET', '/time', version=Defaults.protocol_version)
        ably.close()

    def test_version(self):
        version = "150"  # chosen arbitrarily
        result = self.ably.request('GET', '/time', "150")
        assert result.response.request.headers["X-Ably-Version"] == version
