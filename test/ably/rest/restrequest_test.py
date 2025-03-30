import niquests
import pytest
import responses

from ably import AblyRest
from ably.http.paginatedresult import HttpPaginatedResponse
from ably.transport.defaults import Defaults
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol


# RSC19
class TestRestRequest(BaseAsyncTestCase, metaclass=VaryByProtocolTestsMetaclass):

    async def asyncSetUp(self):
        self.ably = await TestApp.get_ably_rest()
        self.test_vars = await TestApp.get_test_vars()

        # Populate the channel (using the new api)
        self.channel = self.get_channel_name()
        self.path = '/channels/%s/messages' % self.channel
        for i in range(20):
            body = {'name': 'event%s' % i, 'data': 'lorem ipsum %s' % i}
            await self.ably.request('POST', self.path, body=body, version=Defaults.protocol_version)

    async def asyncTearDown(self):
        await self.ably.close()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    async def test_post(self):
        body = {'name': 'test-post', 'data': 'lorem ipsum'}
        result = await self.ably.request('POST', self.path, body=body, version=Defaults.protocol_version)

        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        # HP3
        assert type(result.items) is list
        assert len(result.items) == 1
        assert result.items[0]['channel'] == self.channel
        assert 'messageId' in result.items[0]

    async def test_get(self):
        params = {'limit': 10, 'direction': 'forwards'}
        result = await self.ably.request('GET', self.path, params=params, version=Defaults.protocol_version)

        assert isinstance(result, HttpPaginatedResponse)  # RSC19d

        # HP2
        assert isinstance(await result.next(), HttpPaginatedResponse)
        assert isinstance(await result.first(), HttpPaginatedResponse)

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
    async def test_not_found(self):
        result = await self.ably.request('GET', '/not-found', version=Defaults.protocol_version)
        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        assert result.status_code == 404             # HP4
        assert result.success is False               # HP5

    @dont_vary_protocol
    async def test_error(self):
        params = {'limit': 'abc'}
        result = await self.ably.request('GET', self.path, params=params, version=Defaults.protocol_version)
        assert isinstance(result, HttpPaginatedResponse)  # RSC19d
        assert result.status_code == 400  # HP4
        assert not result.success
        assert result.error_code
        assert result.error_message

    async def test_headers(self):
        key = 'X-Test'
        value = 'lorem ipsum'
        result = await self.ably.request('GET', '/time', headers={key: value}, version=Defaults.protocol_version)
        assert result.response.request.headers[key] == value

    # RSC19e
    @dont_vary_protocol
    async def test_timeout(self):
        # Timeout
        timeout = 0.000001
        ably = AblyRest(token="foo", http_request_timeout=timeout)
        assert ably.http.http_request_timeout == timeout

        with pytest.raises(niquests.ReadTimeout):
            await ably.request('GET', '/time', version=Defaults.protocol_version)
        await ably.close()

        responses.start()

        default_endpoint = 'https://sandbox-rest.ably.io/time'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/time'
        ably = await TestApp.get_ably_rest(fallback_hosts=[fallback_host])

        def _force_err():
            raise niquests.ConnectionError()

        responses.add_callback(
            "GET",
            default_endpoint,
            _force_err,
        )
        responses.get(fallback_endpoint, status=200, content_type="application/json", body='[123]')

        await ably.request('GET', '/time', version=Defaults.protocol_version)
        await ably.close()

        # Bad host, no Fallback
        ably = AblyRest(key=self.test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=self.test_vars["port"],
                        tls_port=self.test_vars["tls_port"],
                        tls=self.test_vars["tls"])
        with pytest.raises(niquests.ConnectionError):
            await ably.request('GET', '/time', version=Defaults.protocol_version)

        responses.stop()
        responses.reset()
        await ably.close()

    # RSC15l3
    @dont_vary_protocol
    async def test_503_status_fallback(self):
        default_endpoint = 'https://sandbox-rest.ably.io/time'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/time'
        ably = await TestApp.get_ably_rest(fallback_hosts=[fallback_host])

        responses.start()

        default_route = responses.get(default_endpoint, status=503, content_type="application/json")
        responses.get(fallback_endpoint, status=200, content_type="application/json", body="[123]")

        result = await ably.request('GET', '/time', version=Defaults.protocol_version)
        assert default_route.call_count
        assert result.status_code == 200
        assert result.items[0] == 123

        responses.stop()
        responses.reset()
        await ably.close()

    # RSC15l2
    @dont_vary_protocol
    async def test_httpx_timeout_fallback(self):
        default_endpoint = 'https://sandbox-rest.ably.io/time'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/time'
        ably = await TestApp.get_ably_rest(fallback_hosts=[fallback_host])
        responses.start()

        def _throw_timeout():
            raise niquests.ReadTimeout

        responses.add_callback(
            "GET",
            default_endpoint,
            callback=_throw_timeout,
        )
        responses.get(
            fallback_endpoint,
            status=200,
            content_type="application/json",
            body="[123]"
        )

        result = await ably.request('GET', '/time', version=Defaults.protocol_version)
        assert any(c.request.url == default_endpoint for c in responses.calls)
        assert result.status_code == 200
        assert result.items[0] == 123

        responses.stop()
        responses.reset()

        await ably.close()

    # RSC15l3
    @dont_vary_protocol
    async def test_503_status_fallback_on_publish(self):
        default_endpoint = 'https://sandbox-rest.ably.io/channels/test/messages'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/channels/test/messages'

        fallback_response_text = (
            '{"id": "unique_id:0", "channel": "test", "name": "test", "data": "data", '
            '"clientId": null, "connectionId": "connection_id", "timestamp": 1696944145000, '
            '"encoding": null}'
        )

        ably = await TestApp.get_ably_rest(fallback_hosts=[fallback_host])
        responses.start()
        default_route = responses.post(default_endpoint, status=503, content_type="application/json")
        responses.post(fallback_endpoint, status=200, content_type="application/json", body=fallback_response_text)
        message_response = await ably.channels['test'].publish('test', 'data')
        assert default_route.call_count
        assert message_response.to_native()['data'] == 'data'
        responses.stop()
        responses.reset()
        await ably.close()

    # RSC15l4
    @dont_vary_protocol
    async def test_400_cloudfront_fallback(self):
        default_endpoint = 'https://sandbox-rest.ably.io/time'
        fallback_host = 'sandbox-a-fallback.ably-realtime.com'
        fallback_endpoint = f'https://{fallback_host}/time'
        ably = await TestApp.get_ably_rest(fallback_hosts=[fallback_host])

        responses.start()

        headers = {
            "Server": "CloudFront",
        }

        default_route = responses.get(
            default_endpoint,
            status=400,
            headers=headers,
            content_type="application/json",
            body="[456]"
        )
        responses.get(
            fallback_endpoint,
            status=200,
            headers=headers,
            content_type="application/json",
            body="[123]"
        )

        result = await ably.request('GET', '/time', version=Defaults.protocol_version)
        assert default_route.call_count
        assert result.status_code == 200
        assert result.items[0] == 123
        responses.stop()
        responses.reset()

        await ably.close()

    async def test_version(self):
        version = "150"  # chosen arbitrarily
        result = await self.ably.request('GET', '/time', "150")
        assert result.response.request.headers["X-Ably-Version"] == version
