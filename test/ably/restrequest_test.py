import pytest
import requests

from ably import AblyRest
from ably.http.paginatedresult import HttpPaginatedResponse
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()


# RSC19
class TestRestRequest(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    @classmethod
    def setUpClass(cls):
        cls.ably = RestSetup.get_ably_rest()

        # Populate the channel (using the new api)
        cls.channel = cls.get_channel_name()
        cls.path = '/channels/%s/messages' % cls.channel
        for i in range(20):
            body = {'name': 'event%s' % i, 'data': 'lorem ipsum %s' % i}
            cls.ably.request('POST', cls.path, body=body)

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_post(self):
        body = {'name': 'test-post', 'data': 'lorem ipsum'}
        result = self.ably.request('POST', self.path, body=body)

        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        # HP3
        assert type(result.items) is list
        assert len(result.items) == 1
        assert result.items[0]['channel'] == self.channel
        assert 'messageId' in result.items[0]

    def test_get(self):
        params = {'limit': 10, 'direction': 'forwards'}
        result = self.ably.request('GET', self.path, params=params)

        assert isinstance(result, HttpPaginatedResponse)  # RSC19d

        # HP2
        assert isinstance(result.next(), HttpPaginatedResponse)
        assert isinstance(result.first(), HttpPaginatedResponse)

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
        result = self.ably.request('GET', '/not-found')
        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        assert result.status_code == 404             # HP4
        assert result.success is False               # HP5

    @dont_vary_protocol
    def test_error(self):
        params = {'limit': 'abc'}
        result = self.ably.request('GET', self.path, params=params)
        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        assert result.status_code == 400  # HP4
        assert not result.success
        assert result.error_code
        assert result.error_message

    def test_headers(self):
        key = 'X-Test'
        value = 'lorem ipsum'
        result = self.ably.request('GET', '/time', headers={key: value})
        assert result.response.request.headers[key] == value

    # RSC19e
    @dont_vary_protocol
    def test_timeout(self):
        # Timeout
        timeout = 0.000001
        ably = AblyRest(token="foo", http_request_timeout=timeout)
        assert ably.http.http_request_timeout == timeout
        with pytest.raises(requests.exceptions.ReadTimeout):
            ably.request('GET', '/time')

        # Bad host, use fallback
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        fallback_hosts_use_default=True)
        result = ably.request('GET', '/time')
        assert isinstance(result, HttpPaginatedResponse)
        assert len(result.items) == 1
        assert isinstance(result.items[0], int)

        # Bad host, no Fallback
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"])
        with pytest.raises(requests.exceptions.ConnectionError):
            ably.request('GET', '/time')
