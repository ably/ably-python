import respx
from httpx import Response

from ably.sync.http.paginatedresult import PaginatedResult

from test.ably.sync.testapp import TestApp
from test.ably.sync.utils import BaseAsyncTestCase


class TestPaginatedResult(BaseAsyncTestCase):

    def get_response_callback(self, headers, body, status):
        def callback(request):
            res = request.url.params.get('page')
            if res:
                return Response(
                    status_code=status,
                    headers=headers,
                    content='[{"page": %i}]' % int(res)
                )

            return Response(
                status_code=status,
                headers=headers,
                content=body
            )

        return callback

    def setUp(self):
        self.ably = TestApp.get_ably_rest(use_binary_protocol=False)
        # Mocked responses
        # without specific headers
        self.mocked_api = respx.mock(base_url='http://rest.ably.io')
        self.ch1_route = self.mocked_api.get('/channels/channel_name/ch1')
        self.ch1_route.return_value = Response(
            headers={'content-type': 'application/json'},
            status_code=200,
            content='[{"id": 0}, {"id": 1}]',
        )
        # with headers
        self.ch2_route = self.mocked_api.get('/channels/channel_name/ch2')
        self.ch2_route.side_effect = self.get_response_callback(
            headers={
                'content-type': 'application/json',
                'link':
                    '<http://rest.ably.io/channels/channel_name/ch2?page=1>; rel="first",'
                    ' <http://rest.ably.io/channels/channel_name/ch2?page=2>; rel="next"'
            },
            body='[{"id": 0}, {"id": 1}]',
            status=200
        )
        # start intercepting requests
        self.mocked_api.start()

        self.paginated_result = PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch1',
            response_processor=lambda response: response.to_native())
        self.paginated_result_with_headers = PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch2',
            response_processor=lambda response: response.to_native())

    def tearDown(self):
        self.mocked_api.stop()
        self.mocked_api.reset()
        self.ably.close()

    def test_items(self):
        assert len(self.paginated_result.items) == 2

    def test_with_no_headers(self):
        assert self.paginated_result.first() is None
        assert self.paginated_result.next() is None
        assert self.paginated_result.is_last()

    def test_with_next(self):
        pag = self.paginated_result_with_headers
        assert pag.has_next()
        assert not pag.is_last()

    def test_first(self):
        pag = self.paginated_result_with_headers
        pag = pag.first()
        assert pag.items[0]['page'] == 1

    def test_next(self):
        pag = self.paginated_result_with_headers
        pag = pag.next()
        assert pag.items[0]['page'] == 2
