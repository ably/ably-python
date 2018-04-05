#import time
import random
import string

import requests
import six

from ably import AblyRest
from ably.http.paginatedresult import HttpPaginatedResponse
from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase
from test.ably.utils import VaryByProtocolTestsMetaclass, dont_vary_protocol

test_vars = RestSetup.get_test_vars()


# RSC19
@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestRestRequest(BaseTestCase):

    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        # Populate the channel (using the new api)
        cls.channel = ''.join([random.choice(string.ascii_letters) for x in range(8)])
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

        self.assertIsInstance(result, HttpPaginatedResponse)  # RSC19d

        # HP2
        self.assertIsInstance(result.next(), HttpPaginatedResponse)
        self.assertIsInstance(result.first(), HttpPaginatedResponse)

        # HP3
        self.assertIsInstance(result.items, list)
        item = result.items[0]
        self.assertIsInstance(item, dict)
        self.assertIn('timestamp', item)
        self.assertIn('id', item)
        self.assertEqual(item['name'], 'event0')
        self.assertEqual(item['data'], 'lorem ipsum 0')

        self.assertEqual(result.status_code, 200)     # HP4
        self.assertEqual(result.success, True)        # HP5
        self.assertEqual(result.error_code, None)     # HP6
        self.assertEqual(result.error_message, None)  # HP7
        self.assertIsInstance(result.headers, list)   # HP7

    @dont_vary_protocol
    def test_not_found(self):
        result = self.ably.request('GET', '/not-found')
        self.assertIsInstance(result, HttpPaginatedResponse)  # RSC19d
        self.assertEqual(result.status_code, 404)             # HP4
        self.assertEqual(result.success, False)               # HP5

    @dont_vary_protocol
    def test_error(self):
        params = {'limit': 'abc'}
        result = self.ably.request('GET', self.path, params=params)
        self.assertIsInstance(result, HttpPaginatedResponse)  # RSC19d
        self.assertEqual(result.status_code, 400)  # HP4
        self.assertFalse(result.success)
        self.assertTrue(result.error_code)
        self.assertTrue(result.error_message)

    def test_headers(self):
        key = 'X-Test'
        value = 'lorem ipsum'
        result = self.ably.request('GET', '/time', headers={key: value})
        self.assertEqual(result.response.request.headers[key], value)

    # RSC19e
    @dont_vary_protocol
    def test_timeout(self):
        # Timeout
        timeout = 0.000001
        ably = AblyRest(token="foo", http_request_timeout=timeout)
        self.assertEqual(ably.http.http_request_timeout, timeout)
        with self.assertRaises(requests.exceptions.ReadTimeout):
            ably.request('GET', '/time')

        # Bad host, use fallback
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"],
                        fallback_hosts_use_default=True)
        result = ably.request('GET', '/time')
        self.assertIsInstance(result, HttpPaginatedResponse)
        self.assertEqual(len(result.items), 1)
        self.assertIsInstance(result.items[0], int)

        # Bad host, no Fallback
        ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                        rest_host='some.other.host',
                        port=test_vars["port"],
                        tls_port=test_vars["tls_port"],
                        tls=test_vars["tls"])
        with self.assertRaises(requests.exceptions.ConnectionError):
            ably.request('GET', '/time')
