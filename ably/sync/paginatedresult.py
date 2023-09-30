from ably.executer.decorator import force_sync
from ably.http.paginatedresult import PaginatedResult
from ably.http.http import Request


class PaginatedResultSync(PaginatedResult):

    @force_sync
    async def first(self):
        return await super().first()

    @force_sync
    async def next(self):
        return await super().next()

    @classmethod
    @force_sync
    async def paginated_query(cls, http, method='GET', url='/', version=None, body=None,
                              headers=None, response_processor=None, raise_on_error=True):
        headers = headers or {}
        req = Request(method, url, version=version, body=body, headers=headers, skip_auth=False,
                      raise_on_error=raise_on_error)
        return await cls.paginated_query_with_request(http, req, response_processor)

    @classmethod
    @force_sync
    async def paginated_query_with_request(cls, http, request, response_processor, raise_on_error=True):
        response = await http.make_request(
            request.method, request.url, version=request.version,
            headers=request.headers, body=request.body,
            skip_auth=request.skip_auth, raise_on_error=request.raise_on_error)

        items = response_processor(response)

        content_type = response.headers['Content-Type']
        links = response.links
        if 'first' in links:
            first_rel_request = request.with_relative_url(links['first']['url'])
        else:
            first_rel_request = None

        if 'next' in links:
            next_rel_request = request.with_relative_url(links['next']['url'])
        else:
            next_rel_request = None

        return cls(http, items, content_type, first_rel_request,
                   next_rel_request, response_processor, response)
