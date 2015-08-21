from __future__ import absolute_import

import unittest
import time

import mock
import requests

from ably import AblyRest


class TestRestHttp(unittest.TestCase):
    def test_max_retry_attempts_and_timeouts(self):
        ably = AblyRest(token="foo")
        self.assertIn('single_request_connect_timeout', ably.http.CONNECTION_RETRY)
        self.assertIn('single_request_read_timeout', ably.http.CONNECTION_RETRY)
        self.assertIn('max_retry_attempts', ably.http.CONNECTION_RETRY)

        with mock.patch('requests.sessions.Session.send',
                        side_effect=requests.exceptions.RequestException) as send_mock:
            try:
                ably.http.make_request('GET', '/', skip_auth=True)
            except requests.exceptions.RequestException:
                pass

            self.assertEqual(
                send_mock.call_count,
                ably.http.CONNECTION_RETRY['max_retry_attempts'])
            self.assertEqual(
                send_mock.call_args,
                mock.call(mock.ANY, timeout=(ably.http.CONNECTION_RETRY['single_request_connect_timeout'],
                                             ably.http.CONNECTION_RETRY['single_request_read_timeout'])))

    def test_cumulative_timeout(self):
        ably = AblyRest(token="foo")
        self.assertIn('cumulative_timeout', ably.http.CONNECTION_RETRY)

        cumulative_timeout_original_value = ably.http.CONNECTION_RETRY['cumulative_timeout']
        ably.http.CONNECTION_RETRY['cumulative_timeout'] = 0.5

        def sleep_and_raise(*args, **kwargs):
            time.sleep(0.51)
            raise requests.exceptions.RequestException
        with mock.patch('requests.sessions.Session.send',
                        side_effect=sleep_and_raise) as send_mock:
            try:
                ably.http.make_request('GET', '/', skip_auth=True)
            except requests.exceptions.RequestException:
                pass

            self.assertEqual(send_mock.call_count, 1)

        ably.http.CONNECTION_RETRY['cumulative_timeout'] = cumulative_timeout_original_value
