from urllib.parse import parse_qs, urlparse

import responses

from ably.http.paginatedresult import PaginatedResult

from test.ably.testapp import TestApp
from test.ably.utils import BaseAsyncTestCase


class TestPaginatedResult(BaseAsyncTestCase):

    def get_response_callback(self, headers, body, status):
        def callback(request):
            params = parse_qs(urlparse(request.url).query)
            res = params["page"][0] if "page" in params else None

            if res:
                return (
                    status,
                    headers,
                    '[{"page": %i}]' % int(res)
                )

            return (
                status,
                headers,
                body,
            )

        return callback

    async def asyncSetUp(self):
        self.ably = await TestApp.get_ably_rest(use_binary_protocol=False)
        # Mocked responses
        # without specific headers
        self.ch1_route = responses.get(
            "http://rest.ably.io/channels/channel_name/ch1",
            content_type="application/json",
            status=200,
            body='[{"id": 0}, {"id": 1}]'
        )

        # with headers
        responses.add_callback(
            "GET",
            "http://rest.ably.io/channels/channel_name/ch2",
            self.get_response_callback(
                headers={
                    'content-type': 'application/json',
                    'link':
                        '<http://rest.ably.io/channels/channel_name/ch2?page=1>; rel="first",'
                        ' <http://rest.ably.io/channels/channel_name/ch2?page=2>; rel="next"'
                },
                body='[{"id": 0}, {"id": 1}]',
                status=200
            ),
            content_type="application/json",
        )

        # start intercepting requests
        responses.start()

        self.paginated_result = await PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch1',
            response_processor=lambda response: response.to_native())
        self.paginated_result_with_headers = await PaginatedResult.paginated_query(
            self.ably.http,
            url='http://rest.ably.io/channels/channel_name/ch2',
            response_processor=lambda response: response.to_native())

    async def asyncTearDown(self):
        responses.stop()
        responses.reset()
        await self.ably.close()

    def test_items(self):
        assert len(self.paginated_result.items) == 2

    async def test_with_no_headers(self):
        assert await self.paginated_result.first() is None
        assert await self.paginated_result.next() is None
        assert self.paginated_result.is_last()

    def test_with_next(self):
        pag = self.paginated_result_with_headers
        assert pag.has_next()
        assert not pag.is_last()

    async def test_first(self):
        pag = self.paginated_result_with_headers
        pag = await pag.first()
        assert pag.items[0]['page'] == 1

    async def test_next(self):
        pag = self.paginated_result_with_headers
        pag = await pag.next()
        assert pag.items[0]['page'] == 2
