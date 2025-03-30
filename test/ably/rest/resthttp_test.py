import base64
import json
import re
import time
from collections import OrderedDict

import mock
import niquests
import pytest
from urllib.parse import urljoin, urlparse, parse_qs

import responses

from ably import AblyRest
from ably.transport.defaults import Defaults
from ably.types.options import Options
from ably.util.exceptions import AblyException
from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase


class TestRestHttp(BaseAsyncTestCase):
    async def test_max_retry_attempts_and_timeouts_defaults(self):
        ably = AblyRest(token="foo")
        assert 'http_open_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS
        assert 'http_request_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS

        with mock.patch('niquests.AsyncSession.send', side_effect=niquests.RequestException()) as send_mock:
            with pytest.raises(niquests.RequestException):
                await ably.http.make_request('GET', '/', version=Defaults.protocol_version, skip_auth=True)

            assert send_mock.call_count == Defaults.http_max_retry_count
            assert send_mock.call_args == mock.call(
                mock.ANY,
                timeout=(4, 10),
                allow_redirects=True,
                proxies=OrderedDict(),
                stream=False,
                verify=True,
                cert=None
            )
        await ably.close()

    async def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        assert 'http_max_retry_duration' in ably.http.CONNECTION_RETRY_DEFAULTS

        ably.options.http_max_retry_duration = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise niquests.Timeout()

        with mock.patch('niquests.AsyncSession.send', side_effect=sleep_and_raise) as send_mock:
            with pytest.raises(niquests.Timeout):
                await ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == 1
        await ably.close()

    async def test_host_fallback(self):
        ably = AblyRest(token="foo")

        def make_url(host):
            base_url = "%s://%s:%d" % (ably.http.preferred_scheme,
                                       host,
                                       ably.http.preferred_port)
            if base_url.endswith(":443") or base_url.endswith(":80"):
                base_url = base_url.replace(":443", "").replace(":80", "")
            return urljoin(base_url, '/')

        with mock.patch('niquests.AsyncSession.send', side_effect=niquests.RequestException) as send_mock:
            with pytest.raises(niquests.RequestException):
                await ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == Defaults.http_max_retry_count

            expected_urls_set = {
                make_url(host)
                for host in Options(http_max_retry_count=10).get_rest_hosts()
            }
            expected_hosts_set = set(Options(http_max_retry_count=10).get_rest_hosts())
            for (prep_request_tuple, _) in send_mock.call_args_list:
                url = prep_request_tuple[0].url
                assert url in expected_urls_set
                expected_urls_set.remove(url)
                current_host = urlparse(prep_request_tuple[0].url).hostname
                assert current_host in expected_hosts_set
                expected_hosts_set.remove(current_host)
        await ably.close()

    @responses.activate
    async def test_no_host_fallback_nor_retries_if_custom_host(self):
        custom_host = 'example.org'
        ably = AblyRest(token="foo", rest_host=custom_host)

        def _throw_error(*args, **kwargs):
            raise niquests.RequestException

        responses.add_callback(
            "GET",
            "https://example.org/",
            _throw_error
        )

        with pytest.raises(niquests.RequestException):
            await ably.http.make_request('GET', '/', skip_auth=True)

        assert len(responses.calls) == 1

        await ably.close()

    # RSC15f
    async def test_cached_fallback(self):
        timeout = 2000
        ably = await TestApp.get_ably_rest(fallback_retry_timeout=timeout)
        host = ably.options.get_rest_host()

        state = {'errors': 0}
        client = niquests.AsyncSession()
        send = client.send

        async def side_effect(*args, **kwargs):
            if f"://{host}" in args[1].url:
                state['errors'] += 1
                raise RuntimeError
            return await send(args[1])

        with mock.patch('niquests.AsyncSession.send', side_effect=side_effect, autospec=True):
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

        await client.close()
        await ably.close()

    @responses.activate
    async def test_no_retry_if_not_500_to_599_http_code(self):
        default_host = Options().get_rest_host()
        ably = AblyRest(token="foo")

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        default_url = default_url.replace(":443/", "/")

        mock_route = responses.get(
            default_url,
            status=600,
            content_type="application/json",
            body=json.dumps({'message': "", 'status_code': 600, 'code': 50500}),
        )

        with pytest.raises(AblyException):
            await ably.http.make_request('GET', '/', skip_auth=True)

        assert mock_route.call_count == 1
        assert len(responses.calls) == 1

        await ably.close()

    @responses.activate
    async def test_500_errors(self):
        """
        Raise error if all the servers reply with a 5xx error.
        https://github.com/ably/ably-python/issues/160
        """

        ably = AblyRest(token="foo")

        mock_request = responses.get(
            re.compile(r"(.*)"),
            status=500,
            body="Internal Server Error"
        )

        with pytest.raises(AblyException):
            await ably.http.make_request('GET', '/', skip_auth=True)

        assert mock_request.call_count == 3

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
        ably = await TestApp.get_ably_rest()
        r = await ably.http.make_request('HEAD', '/time', skip_auth=True)

        # API
        assert 'X-Ably-Version' in r.request.headers
        assert r.request.headers['X-Ably-Version'] == '3'

        # Agent
        assert 'Ably-Agent' in r.request.headers
        expr = r"^ably-python\/\d+.\d+.\d+(-beta\.\d+)? python\/\d.\d+.\d+$"
        assert re.search(expr, r.request.headers['Ably-Agent'])
        await ably.close()

    # RSC7c
    async def test_add_request_ids(self):
        # With request id
        ably = await TestApp.get_ably_rest(add_request_ids=True)
        r = await ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id=' in r.request.url
        request_id1 = parse_qs(urlparse(r.request.url).query)['request_id'][0]
        assert len(base64.urlsafe_b64decode(request_id1)) == 12

        # With request id and new request
        r = await ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id=' in r.request.url
        request_id2 = parse_qs(urlparse(r.request.url).query)['request_id'][0]
        assert len(base64.urlsafe_b64decode(request_id2)) == 12
        assert request_id1 != request_id2
        await ably.close()

        # With request id and new request
        ably = await TestApp.get_ably_rest()
        r = await ably.http.make_request('HEAD', '/time', skip_auth=True)
        assert 'request_id=' not in r.request.url
        await ably.close()

    @responses.activate
    async def test_request_over_http2(self):
        url = 'https://www.example.com/'

        responses.get(url=url, status=200)

        ably = await TestApp.get_ably_rest(rest_host=url)
        r = await ably.http.make_request('GET', url, skip_auth=True)
        assert r.http_version == 0  # mocked dummy response don't have a http version
        await ably.close()
