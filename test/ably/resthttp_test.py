import re
import time

import httpx
import mock
import pytest
from urllib.parse import urljoin

import respx
from httpx import Response

from ably import AblyRest
from ably.transport.defaults import Defaults
from ably.types.options import Options
from ably.util.exceptions import AblyException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseAsyncTestCase


class TestRestHttp(BaseAsyncTestCase):
    async def test_max_retry_attempts_and_timeouts_defaults(self):
        ably = AblyRest(token="foo")
        assert 'http_open_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS
        assert 'http_request_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS

        with mock.patch('httpx.AsyncClient.send', side_effect=httpx.RequestError('')) as send_mock:
            with pytest.raises(httpx.RequestError):
                await ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == Defaults.http_max_retry_count
            assert send_mock.call_args == mock.call(mock.ANY)
        await ably.close()

    async def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        assert 'http_max_retry_duration' in ably.http.CONNECTION_RETRY_DEFAULTS

        ably.options.http_max_retry_duration = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise httpx.TimeoutException('timeout')

        with mock.patch('httpx.AsyncClient.send', side_effect=sleep_and_raise) as send_mock:
            with pytest.raises(httpx.TimeoutException):
                await ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == 1
        await ably.close()

    async def test_host_fallback(self):
        ably = AblyRest(token="foo")

        def make_url(host):
            base_url = "%s://%s:%d" % (ably.http.preferred_scheme,
                                       host,
                                       ably.http.preferred_port)
            return urljoin(base_url, '/')

        with mock.patch('httpx.Request', wraps=httpx.Request) as request_mock:
            with mock.patch('httpx.AsyncClient.send', side_effect=httpx.RequestError('')) as send_mock:
                with pytest.raises(httpx.RequestError):
                    await ably.http.make_request('GET', '/', skip_auth=True)

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
        await ably.close()

    @pytest.mark.skip(reason="skipped due to httpx changes")
    async def test_no_host_fallback_nor_retries_if_custom_host(self):
        custom_host = 'example.org'
        ably = AblyRest(token="foo", rest_host=custom_host)

        custom_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            custom_host,
            ably.http.preferred_port)

        with mock.patch('httpx.Request', wraps=httpx.Request) as request_mock:
            with mock.patch('httpx.AsyncClient.send', side_effect=httpx.RequestError('')) as send_mock:
                with pytest.raises(httpx.RequestError):
                    await ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 1
                assert request_mock.call_args == mock.call(mock.ANY,
                                                           custom_url,
                                                           content=mock.ANY,
                                                           headers=mock.ANY)
        await ably.close()

    # RSC15f
    @pytest.mark.filterwarnings('ignore::DeprecationWarning')
    async def test_cached_fallback(self):
        timeout = 2000
        ably = await RestSetup.get_ably_rest(fallback_hosts_use_default=True, fallback_retry_timeout=timeout)
        host = ably.options.get_rest_host()

        state = {'errors': 0}
        client = httpx.AsyncClient(http2=True)
        send = client.send

        def side_effect(*args, **kwargs):
            if args[1].url.host == host:
                state['errors'] += 1
                raise RuntimeError
            return send(args[1])

        with mock.patch('httpx.AsyncClient.send', side_effect=side_effect, autospec=True):
            # The main host is called and there's an error
            await ably.time()
            assert state['errors'] == 1

            # The cached host is used: no error
            await ably.time()
            await ably.time()
            await ably.time()
            assert state['errors'] == 1

            # The cached host has expired, we've an error again
            time.sleep(timeout / 1000.0)
            await ably.time()
            assert state['errors'] == 2

        await client.aclose()
        await ably.close()

    @pytest.mark.skip(reason="skipped due to httpx changes")
    async def test_no_retry_if_not_500_to_599_http_code(self):
        default_host = Options().get_rest_host()
        ably = AblyRest(token="foo")

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        def raise_ably_exception(*args, **kwargs):
            raise AblyException(message="", status_code=600, code=50500)

        with mock.patch('httpx.Request', wraps=httpx.Request) as request_mock:
            with mock.patch('ably.util.exceptions.AblyException.raise_for_response',
                            side_effect=raise_ably_exception) as send_mock:
                with pytest.raises(AblyException):
                    await ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 1
                assert request_mock.call_args == mock.call(mock.ANY,
                                                           default_url,
                                                           content=mock.ANY,
                                                           headers=mock.ANY)
        await ably.close()

    async def test_500_errors(self):
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
                    await ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 3
        await ably.close()

    def test_custom_http_timeouts(self):
        ably = AblyRest(
            token="foo", http_request_timeout=30, http_open_timeout=8,
            http_max_retry_count=6, http_max_retry_duration=20)

        assert ably.http.http_request_timeout == 30
        assert ably.http.http_open_timeout == 8
        assert ably.http.http_max_retry_count == 6
        assert ably.http.http_max_retry_duration == 20

    # RSC7a, RSC7b
    async def test_request_headers(self):
        ably = await RestSetup.get_ably_rest()
        r = await ably.http.make_request('HEAD', '/time', skip_auth=True)

        # API
        assert 'X-Ably-Version' in r.request.headers
        assert r.request.headers['X-Ably-Version'] == '1.2'

        # Agent
        assert 'Ably-Agent' in r.request.headers
        expr = r"^ably-python\/\d.\d.\d python\/\d.\d+.\d+$"
        assert re.search(expr, r.request.headers['Ably-Agent'])
        await ably.close()

    async def test_request_over_http2(self):
        url = 'https://www.example.com'
        respx.get(url).mock(return_value=Response(status_code=200))

        ably = await RestSetup.get_ably_rest(rest_host=url)
        r = await ably.http.make_request('GET', url, skip_auth=True)
        assert r.http_version == 'HTTP/2'
        await ably.close()
