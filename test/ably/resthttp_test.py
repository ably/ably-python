from __future__ import absolute_import

import time

import mock
import requests
from six.moves.urllib.parse import urljoin

from ably import AblyRest
from ably.transport.defaults import Defaults
from ably.types.options import Options
from ably.util.exceptions import AblyException
from test.ably.utils import BaseTestCase


class TestRestHttp(BaseTestCase):
    def test_max_retry_attempts_and_timeouts_defaults(self):
        ably = AblyRest(token="foo")
        self.assertIn('http_open_timeout', ably.http.CONNECTION_RETRY_DEFAULTS)
        self.assertIn('http_request_timeout', ably.http.CONNECTION_RETRY_DEFAULTS)
        self.assertIn('http_max_retry_count', ably.http.CONNECTION_RETRY_DEFAULTS)

        with mock.patch('requests.sessions.Session.send',
                        side_effect=requests.exceptions.RequestException) as send_mock:
            with self.assertRaises(requests.exceptions.RequestException):
                ably.http.make_request('GET', '/', skip_auth=True)

            self.assertEqual(
                send_mock.call_count,
                ably.http.CONNECTION_RETRY_DEFAULTS['http_max_retry_count'])
            self.assertEqual(
                send_mock.call_args,
                mock.call(mock.ANY, timeout=(ably.http.CONNECTION_RETRY_DEFAULTS['http_open_timeout'],
                                             ably.http.CONNECTION_RETRY_DEFAULTS['http_request_timeout'])))

    def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        self.assertIn('http_max_retry_duration', ably.http.CONNECTION_RETRY_DEFAULTS)

        ably.options.http_max_retry_duration = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise requests.exceptions.RequestException

        with mock.patch('requests.sessions.Session.send',
                        side_effect=sleep_and_raise) as send_mock:
            with self.assertRaises(requests.exceptions.RequestException):
                ably.http.make_request('GET', '/', skip_auth=True)

            self.assertEqual(send_mock.call_count, 1)

    def test_host_fallback(self):
        ably = AblyRest(token="foo")
        self.assertIn('http_max_retry_count', ably.http.CONNECTION_RETRY_DEFAULTS)

        def make_url(host):
            base_url = "%s://%s:%d" % (ably.http.preferred_scheme,
                                       host,
                                       ably.http.preferred_port)
            return urljoin(base_url, '/')

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('requests.sessions.Session.send',
                            side_effect=requests.exceptions.RequestException) as send_mock:
                with self.assertRaises(requests.exceptions.RequestException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                self.assertEqual(
                    send_mock.call_count,
                    ably.http.CONNECTION_RETRY_DEFAULTS['http_max_retry_count'])

                expected_urls_set = set([
                    make_url(host)
                    for host in ([ably.http.preferred_host] +
                                 Defaults.get_fallback_rest_hosts(Options()))
                ])
                for ((__, url), ___) in request_mock.call_args_list:
                    self.assertIn(url, expected_urls_set)
                    expected_urls_set.remove(url)

    def test_no_host_fallback_nor_retries_if_custom_host(self):
        custom_host = 'example.org'
        ably = AblyRest(token="foo", rest_host=custom_host)
        self.assertIn('http_max_retry_count', ably.http.CONNECTION_RETRY_DEFAULTS)

        custom_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            custom_host,
            ably.http.preferred_port)

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('requests.sessions.Session.send',
                            side_effect=requests.exceptions.RequestException) as send_mock:
                with self.assertRaises(requests.exceptions.RequestException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                self.assertEqual(send_mock.call_count, 1)
                self.assertEqual(
                    request_mock.call_args,
                    mock.call(mock.ANY, custom_url, data=mock.ANY, headers=mock.ANY))

    def test_no_retry_if_not_500_to_599_http_code(self):
        default_host = Defaults.get_rest_host(Options())
        ably = AblyRest(token="foo")
        self.assertIn('http_max_retry_count', ably.http.CONNECTION_RETRY_DEFAULTS)

        default_url = "%s://%s:%d/" % (
            ably.http.preferred_scheme,
            default_host,
            ably.http.preferred_port)

        def raise_ably_exception(*args, **kwagrs):
            raise AblyException(message="",
                                status_code=600,
                                code=50500)

        with mock.patch('requests.Request', wraps=requests.Request) as request_mock:
            with mock.patch('ably.util.exceptions.AblyException.raise_for_response',
                            side_effect=raise_ably_exception) as send_mock:
                with self.assertRaises(AblyException):
                    ably.http.make_request('GET', '/', skip_auth=True)

                self.assertEqual(send_mock.call_count, 1)
                self.assertEqual(
                    request_mock.call_args,
                    mock.call(mock.ANY, default_url, data=mock.ANY, headers=mock.ANY))

    def test_custom_http_timeouts(self):
        ably = AblyRest(
            token="foo", http_request_timeout=30, http_open_timeout=8,
            http_max_retry_count=6, http_max_retry_duration=20)

        self.assertEqual(ably.http.http_request_timeout, 30)
        self.assertEqual(ably.http.http_open_timeout, 8)
        self.assertEqual(ably.http.http_max_retry_count, 6)
        self.assertEqual(ably.http.http_max_retry_duration, 20)
