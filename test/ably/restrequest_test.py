import six

from ably import AblyRest
from ably.http.paginatedresult import HttpPaginatedResult
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
        for i in range(20):
            body = {'name': 'event%s' % i, 'data': 'lorem ipsum %s' % i}
            cls.ably.request('POST', '/channels/test/messages', body=body)

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol
        self.use_binary_protocol = use_binary_protocol

    def test_post(self):
        body = {'name': 'test-post', 'data': 'lorem ipsum'}
        result = self.ably.request('POST', '/channels/test/messages', body=body)

        self.assertIsInstance(result, HttpPaginatedResult) # RSC19d
        self.assertEqual(result.items, [])                 # HP3

    def test_get(self):
        params = {'limit': 10, 'direction': 'forwards'}
        result = self.ably.request('GET', '/channels/test/messages', params=params)

        self.assertIsInstance(result, HttpPaginatedResult) # RSC19d

        # HP2
        self.assertIsInstance(result.next(), HttpPaginatedResult)
        self.assertIsInstance(result.first(), HttpPaginatedResult)

        # HP3
        self.assertIsInstance(result.items, list)
        item = result.items[0]
        self.assertIsInstance(item, dict)
        self.assertIn('timestamp', item)
        self.assertIn('id', item)
        self.assertEqual(item['name'], 'event0')
        self.assertEqual(item['data'], 'lorem ipsum 0')

        self.assertEqual(result.status_code, 200)    # HP4
        self.assertEqual(result.success, True)       # HP5
        self.assertEqual(result.error_code, None)    # HP6
        self.assertEqual(result.error_message, None) # HP7
        self.assertIsInstance(result.headers, list)  # HP7

    @dont_vary_protocol
    def test_not_found(self):
        result = self.ably.request('GET', '/not-found')
        self.assertIsInstance(result, HttpPaginatedResult) # RSC19d
        self.assertEqual(result.status_code, 404)          # HP4
        self.assertEqual(result.success, False)            # HP5

    @dont_vary_protocol
    def test_error(self):
        params = {'limit': 'abc'}
        result = self.ably.request('GET', '/channels/test/messages', params=params)
        self.assertIsInstance(result, HttpPaginatedResult) # RSC19d
        self.assertEqual(result.status_code, 400) # HP4
        self.assertFalse(result.success)
        self.assertTrue(result.error_code)
        self.assertTrue(result.error_message)

    def test_headers(self):
        key = 'X-Test'
        value = 'lorem ipsum'
        result = self.ably.request('GET', '/time', headers={key: value})
        self.assertEqual(result.response.request.headers[key], value)
