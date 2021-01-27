import re
import time

import mock
import pytest
import requests
from urllib.parse import urljoin, urlparse

from ably import AblyRest
from ably.transport.defaults import Defaults
from ably.types.options import Options
from ably.util.exceptions import AblyException
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase


class TestRestHttp(BaseTestCase):
    def test_max_retry_attempts_and_timeouts_defaults(self):
        ably = AblyRest(token="foo")
        assert 'http_open_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS
        assert 'http_request_timeout' in ably.http.CONNECTION_RETRY_DEFAULTS

        with mock.patch('requests.sessions.Session.send',
                        side_effect=requests.exceptions.RequestException) as send_mock:
            with pytest.raises(requests.exceptions.RequestException):
                ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == Defaults.http_max_retry_count
            timeout = (
                ably.http.CONNECTION_RETRY_DEFAULTS['http_open_timeout'],
                ably.http.CONNECTION_RETRY_DEFAULTS['http_request_timeout'],
            )
            assert send_mock.call_args == mock.call(mock.ANY, timeout=timeout)

    def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        assert 'http_max_retry_duration' in ably.http.CONNECTION_RETRY_DEFAULTS

        ably.options.http_max_retry_duration = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise requests.exceptions.RequestException

        with mock.patch('requests.sessions.Session.send',
                        side_effect=sleep_and_raise) as send_mock:
            with pytest.raises(requests.exceptions.RequestException):
                ably.http.make_request('GET', '/', skip_auth=True)

            assert send_mock.call_count == 1

    def test_host_fallback(self):
        ably = AblyRest(token="foo")

        def make_url(host):
            base_url = "%s://%s:%d" % (ably.http.preferred_scheme,
                                       host,
                                       ably.http.preferred_port)
            return urljoin(base_url, '/')

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('requests.sessions.Session.send',
                            side_effect=requests.exceptions.RequestException) as send_mock:
                with pytest.raises(requests.exceptions.RequestException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == Defaults.http_max_retry_count

                expected_urls_set = {
                    make_url(host)
                    for host in Options(http_max_retry_count=10).get_rest_hosts()
                }
                for ((_, url), _) in request_mock.call_args_list:
                    assert url in expected_urls_set
                    expected_urls_set.remove(url)

    def test_no_host_fallback_nor_retries_if_custom_host(self):
        custom_host = 'example.org'
        ably = AblyRest(token="foo", rest_host=custom_host)

        custom_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            custom_host,
            ably.http.preferred_port)

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('requests.sessions.Session.send',
                            side_effect=requests.exceptions.RequestException) as send_mock:
                with pytest.raises(requests.exceptions.RequestException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 1
                assert request_mock.call_args == mock.call(mock.ANY, custom_url, data=mock.ANY, headers=mock.ANY)

    # RSC15f
    def test_cached_fallback(self):
        timeout = 2000
        ably = RestSetup.get_ably_rest(fallback_hosts_use_default=True, fallback_retry_timeout=timeout)
        host = ably.options.get_rest_host()

        state = {'errors': 0}
        send = requests.sessions.Session.send
        def side_effect(self, prepped, *args, **kwargs):
            if urlparse(prepped.url).hostname == host:
                state['errors'] += 1
                raise RuntimeError
            return send(self, prepped, *args, **kwargs)

        with mock.patch('requests.sessions.Session.send', side_effect=side_effect, autospec=True):
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

    def test_no_retry_if_not_500_to_599_http_code(self):
        default_host = Options().get_rest_host()
        ably = AblyRest(token="foo")

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        def raise_ably_exception(*args, **kwagrs):
            raise AblyException(message="", status_code=600, code=50500)

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('ably.util.exceptions.AblyException.raise_for_response',
                            side_effect=raise_ably_exception) as send_mock:
                with pytest.raises(AblyException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 1
                assert request_mock.call_args == mock.call(mock.ANY, default_url, data=mock.ANY, headers=mock.ANY)

    def test_500_errors(self):
        """
        Raise error if all the servers reply with a 5xx error.
        https://github.com/ably/ably-python/issues/160
        """
        default_host = Options().get_rest_host()
        ably = AblyRest(token="foo")

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        def raise_ably_exception(*args, **kwagrs):
            raise AblyException(message="", status_code=500, code=50000)

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('ably.util.exceptions.AblyException.raise_for_response',
                            side_effect=raise_ably_exception) as send_mock:
                with pytest.raises(AblyException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                assert send_mock.call_count == 3

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
        ably = RestSetup.get_ably_rest()
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)

        # API
        assert 'X-Ably-Version' in r.request.headers
        assert r.request.headers['X-Ably-Version'] == '1.1'

        # Lib
        assert 'X-Ably-Lib' in r.request.headers
        expr = r"^python-1\.1\.\d+(-\w+)?$"
        assert re.search(expr, r.request.headers['X-Ably-Lib'])

        # Lib Variant
        ably.set_variant('django')
        r = ably.http.make_request('HEAD', '/time', skip_auth=True)
        expr = r"^python.django-1\.1\.\d+(-\w+)?$"
        assert re.search(expr, r.request.headers['X-Ably-Lib'])
