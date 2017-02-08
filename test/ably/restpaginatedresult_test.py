from __future__ import absolute_import

import re

import responses

from ably import AblyRest
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import BaseTestCase

test_vars = RestSetup.get_test_vars()


class TestPaginatedResult(BaseTestCase):

    def get_response_callback(self, headers, body, status):
        def callback(request):
            res = re.search(r'page=(\d+)', request.url)
            if res:
                return (status, headers, '[{"page": %i}]' % int(res.group(1)))
            return (status, headers, body)

        return callback

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"],
                             use_binary_protocol=False)

        # Mocked responses
        # without headers
        responses.add(responses.GET,
                      'http://rest.ably.io/channels/channel_name/ch1',
                      body='[{"id": 0}, {"id": 1}]', status=200,
                      content_type='application/json')
        # with headers
        responses.add_callback(
            responses.GET,
            'http://rest.ably.io/channels/channel_name/ch2',
            self.get_response_callback(
                headers={
                    'link':
                    '<http://rest.ably.io/channels/channel_name/ch2?page=1>; rel="first",'
                    ' <http://rest.ably.io/channels/channel_name/ch2?page=2>; rel="next"'
                },
                body='[{"id": 0}, {"id": 1}]',
                status=200),
            content_type='application/json')

        # start intercepting requests
        responses.start()

        self.paginated_result = PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch1',
            response_processor=lambda response: response.to_native())
        self.paginated_result_with_headers = PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch2',
            response_processor=lambda response: response.to_native())

    def tearDown(self):
        responses.stop()
        responses.reset()

    def test_items(self):
        self.assertEquals(len(self.paginated_result.items), 2)

    def test_with_no_headers(self):
        self.assertIsNone(self.paginated_result.first())
        self.assertIsNone(self.paginated_result.next())
        self.assertTrue(self.paginated_result.is_last())

    def test_with_next(self):
        pag = self.paginated_result_with_headers
        self.assertTrue(pag.has_next())
        self.assertFalse(pag.is_last())

    def test_first(self):
        pag = self.paginated_result_with_headers
        pag = pag.first()
        self.assertEquals(pag.items[0]['page'], 1)

    def test_next(self):
        pag = self.paginated_result_with_headers
        pag = pag.next()
        self.assertEquals(pag.items[0]['page'], 2)
