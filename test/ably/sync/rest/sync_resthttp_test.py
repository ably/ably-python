import base64
import re
import time

import httpx
import mock
import pytest
from urllib.parse import urljoin

import respx
from httpx import Response

from ably.sync import AblyRest
from ably.sync.transport.defaults import Defaults
from ably.sync.types.options import Options
from ably.sync.util.exceptions import AblyException
from test.ably.sync.testapp import TestApp
from test.ably.sync.utils import BaseAsyncTestCase


class TestRestHttp(BaseAsyncTestCase):
    def test_max_retry_attempts_and_timeouts_defaults(self):
        ably = AblyRest(token="foo")
        assert 'http_open_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS
        assert 'http_request_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS

        with mock.patch('httpx.AsyncClient.send', side_effect=httpx.RequestError('')) as send_mock:
            with pytest.raises(httpx.RequestError):
                ably.http.make_request('GET', '/', version=Defaults.protocol_version, skip_auth=True)

            assert send_mock.call_count == Defaults.http_max_retry_count
            assert send_mock.call_args == mock.call(mock.ANY)
        ably.close()

    def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        assert 'http_max_retry_duration' in ably.http.CONNECTION_RETRY_DEFAULTS

        ably.options.http_max_retry_duration = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise httpx.TimeoutException('timeout')

        with mock.patch('httpx.AsyncClient.send', side_effect=sleep_and_raise) as send_mock:
            with pytest.raises(httpx.TimeoutException):
                ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == 1
        ably.close()

    def test_host_fallback(self):
        ably = AblyRest(token="foo")

        def make_url(host):
            base_url = "%s://%s:%d" % (ably.http.preferred_scheme,
                                       host,
                                       ably.http.preferred_port)
            return urljoin(base_url, '/')

        with mock.patch('httpx.Request', wraps=httpx.Request) as request_mock:
            with mock.patch('httpx.AsyncClient.send', side_effect=httpx.RequestError('')) as send_mock:
                with pytest.raises(httpx.RequestError):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == Defaults.http_max_retry_count

                expected_urls_set = {
                    make_url(host)
                    for host in Options(http_max_retry_count=10).get_rest_hosts()
                }
                for ((_, url), _) in request_mock.call_args_list:
                    assert url in expected_urls_set
                    expected_urls_set.remove(url)

                expected_hosts_set = set(Options(http_max_retry_count=10).get_rest_hosts())
                for (prep_request_tuple, _) in send_mock.call_args_list:
                    assert prep_request_tuple[0].headers.get('host') in expected_hosts_set
                    expected_hosts_set.remove(prep_request_tuple[0].headers.get('host'))
        ably.close()

    @respx.mock
    def test_no_host_fallback_nor_retries_if_custom_host(self):
        custom_host = 'example.org'
        ably = AblyRest(token="foo", rest_host=custom_host)

        mock_route = respx.get("https://example.org").mock(side_effect=httpx.RequestError(''))

        with pytest.raises(httpx.RequestError):
            ably.http.make_request('GET', '/', skip_auth=True)

        assert mock_route.call_count == 1
        assert respx.calls.call_count == 1

        ably.close()

    # RSC15f
    def test_cached_fallback(self):
        timeout = 2000
        ably = TestApp.get_ably_rest(fallback_retry_timeout=timeout)
        host = ably.options.get_rest_host()

        state = {'errors': 0}
        client = httpx.Client(http2=True)
        send = client.send

        def side_effect(*args, **kwargs):
            if args[1].url.host == host:
                state['errors'] += 1
                raise RuntimeError
            return send(args[1])

        with mock.patch('httpx.AsyncClient.send', side_effect=side_effect, autospec=True):
            # The main host is called and there's an error
            ably.time()
            assert state['errors'] == 1

            # The cached host is used: no error
            ably.time()
            ably.time()
            ably.time()
            assert state['errors'] == 1

            # The cached host has expired, we've an error again
            time.sleep(timeout / 1000.0)
            ably.time()
            assert state['errors'] == 2

        client.close()
        ably.close()

    @respx.mock
    def test_no_retry_if_not_500_to_599_http_code(self):
        default_host = Options().get_rest_host()
        ably = AblyRest(token="foo")

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        mock_response = httpx.Response(600, json={'message': "", 'status_code': 600, 'code': 50500})

        mock_route = respx.get(default_url).mock(return_value=mock_response)

        with pytest.raises(AblyException):
            ably.http.make_request('GET', '/', skip_auth=True)

        assert mock_route.call_count == 1
        assert respx.calls.call_count == 1

        ably.close()

    def test_500_errors(self):
        """
        Raise error if all the servers reply with a 5xx error.
        https://github.com/ably/ably-python/issues/160
        """

        ably = AblyRest(token="foo")

        def raise_ably_exception(*args, **kwargs):
            raise AblyException(message="", status_code=500, code=50000)

        with mock.patch('httpx.Request', wraps=httpx.Request):
            with mock.patch('ably.util.exceptions.AblyException.raise_for_response',
                            side_effect=raise_ably_exception) as send_mock:
                with pytest.raises(AblyException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 3
        ably.close()

    def test_custom_http_timeouts(self):
        ably = AblyRest(
            token="foo", http_request_timeout=30, http_open_timeout=8,
            http_max_retry_count=6, http_max_retry_duration=20)

        assert ably.http.http_request_timeout == 30
        assert ably.http.http_open_timeout == 8
        assert ably.http.http_max_retry_count == 6
        assert ably.http.http_max_retry_duration == 20

    # RSC7a, RSC7b
    def test_request_headers(self):
        ably = TestApp.get_ably_rest()
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)

        # API
        assert 'X-Ably-Version' in r.request.headers
        assert r.request.headers['X-Ably-Version'] == '3'

        # Agent
        assert 'Ably-Agent' in r.request.headers
        expr = r"^ably-python\/\d.\d.\d(-beta\.\d)? python\/\d.\d+.\d+$"
        assert re.search(expr, r.request.headers['Ably-Agent'])
        ably.close()

    # RSC7c
    def test_add_request_ids(self):
        # With request id
        ably = TestApp.get_ably_rest(add_request_ids=True)
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id' in r.request.url.params
        request_id1 = r.request.url.params['request_id']
        assert len(base64.urlsafe_b64decode(request_id1)) == 12

        # With request id and new request
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id' in r.request.url.params
        request_id2 = r.request.url.params['request_id']
        assert len(base64.urlsafe_b64decode(request_id2)) == 12
        assert request_id1 != request_id2
        ably.close()

        # With request id and new request
        ably = TestApp.get_ably_rest()
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id' not in r.request.url.params
        ably.close()

    def test_request_over_http2(self):
        url = 'https://www.example.com'
        respx.get(url).mock(return_value=Response(status_code=200))

        ably = TestApp.get_ably_rest(rest_host=url)
        r = ably.http.make_request('GET', url, skip_auth=True)
        assert r.http_version == 'HTTP/2'
        ably.close()
