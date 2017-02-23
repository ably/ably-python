from __future__ import absolute_import

import logging

from ably.http.http import Request

log = logging.getLogger(__name__)


class PaginatedResult(object):
    def __init__(self, http, items, content_type, rel_first, rel_next,
                 response_processor, response):
        self.__http = http
        self.__items = items
        self.__content_type = content_type
        self.__rel_first = rel_first
        self.__rel_next = rel_next
        self.__response_processor = response_processor
        self.response = response

    @property
    def items(self):
        return self.__items

    def has_first(self):
        return self.__rel_first is not None

    def has_next(self):
        return self.__rel_next is not None

    def is_last(self):
        return not self.has_next()

    def first(self):
        return self.__get_rel(self.__rel_first) if self.__rel_first else None

    def next(self):
        return self.__get_rel(self.__rel_next) if self.__rel_next else None

    def __get_rel(self, rel_req):
        if rel_req is None:
            return None
        return self.paginated_query_with_request(self.__http, rel_req, self.__response_processor)

    @classmethod
    def paginated_query(cls, http, method='GET', url='/', body=None,
                        headers=None, response_processor=None,
                        raise_on_error=True):
        headers = headers or {}
        req = Request(method, url, body=body, headers=headers, skip_auth=False,
                      raise_on_error=raise_on_error)
        return cls.paginated_query_with_request(http, req, response_processor)

    @classmethod
    def paginated_query_with_request(cls, http, request, response_processor,
                                     raise_on_error=True):
        response = http.make_request(
            request.method, request.url, headers=request.headers,
            body=request.body, skip_auth=request.skip_auth,
            raise_on_error=request.raise_on_error)

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


class HttpPaginatedResponse(PaginatedResult):
    @property
    def status_code(self):
        return self.response.status_code

    @property
    def success(self):
        status_code = self.status_code
        return status_code >= 200 and status_code < 300

    @property
    def error_code(self):
        return self.response.headers.get('X-Ably-Errorcode')

    @property
    def error_message(self):
        return self.response.headers.get('X-Ably-Errormessage')

    @property
    def headers(self):
        return list(self.response.headers.items())
