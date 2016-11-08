from __future__ import absolute_import

import logging

from ably.http.http import Request
from ably.http.httputils import HttpUtils

log = logging.getLogger(__name__)


class PaginatedResult(object):
    def __init__(self, http, items, content_type, rel_first, rel_next,
                 response_processor):
        self.__http = http
        self.__items = items
        self.__content_type = content_type
        self.__rel_first = rel_first
        self.__rel_next = rel_next
        self.__response_processor = response_processor

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
        return PaginatedResult.paginated_query_with_request(self.__http, rel_req, self.__response_processor)

    @staticmethod
    def paginated_query(http, url, headers, response_processor):
        headers = headers or {}
        req = Request(method='GET', url=url, headers=headers, body=None, skip_auth=False)
        return PaginatedResult.paginated_query_with_request(http, req, response_processor)

    @staticmethod
    def process_paginated_query_response(request, response, response_processor = None):

        if response_processor:
            items = response_processor(response)
        else:
            try:
                items = response.json()
            except:
                items = [ ]

        content_type = response.headers['Content-Type']
        links = response.links
        log.debug("Links: %s" % links)
        log.debug("Response: %s" % response)
        if 'first' in links:
            first_rel_request = request.with_relative_url(links['first']['url'])
        else:
            first_rel_request = None

        if 'next' in links:
            log.debug("Next: %s" % links['next']['url'])
            next_rel_request = request.with_relative_url(links['next']['url'])
            log.debug("Next rel request: %s" % next_rel_request)
        else:
            next_rel_request = None

        return items, content_type, first_rel_request, next_rel_request

    @staticmethod
    def paginated_query_with_request(http, request, response_processor):
        response = http.request(request)

        items, content_type, first_rel_request, next_rel_request = \
                PaginatedResult.process_paginated_query_response(request, response, response_processor)

        return PaginatedResult(http, items, content_type, first_rel_request,
                               next_rel_request, response_processor)

class HttpPaginatedResponse(PaginatedResult):

    def __init__(self, http, items, content_type, rel_first, rel_next, response):

        super(HttpPaginatedResponse, self).__init__(http, items, content_type,
                rel_first, rel_next, None)

        self.__response = response

    @property
    def items(self):
        if not isinstance(self._PaginatedResult__items, list):
            return [ self._PaginatedResult__items ]
        else:
            return self._PaginatedResult__items

    def first(self):
        return self.__get_rel(self._PaginatedResult__rel_first) if self._PaginatedResult__rel_first else None

    def next(self):
        return self.__get_rel(self._PaginatedResult__rel_next) if self._PaginatedResult__rel_next else None

    def __get_rel(self, rel_req):
        if rel_req is None:
            return None
        return HttpPaginatedResponse.http_paginated_response_with_request(self._PaginatedResult__http, rel_req)

    @property
    def status_code(self):
        return self.__response.status_code

    @property
    def success(self):
        return self.__response.status_code >= 200 and self.__response.status_code < 300

    @property
    def header(self):
        return self.__response.headers

    @property
    def errorCode(self):
        if "X-Ably-Errorcode" in self.__response.headers:
            return self.__response.headers["X-Ably-Errorcode"]

    @property
    def errorMessage(self):
        if "X-Ably-Errormessage" in self.__response.headers:
            return self.__response.headers["X-Ably-Errormessage"]

    @staticmethod
    def paginated_response(http, method, url, headers):
        headers = headers or {}
        req = Request(method=method, url=url, headers=headers, body=None, skip_auth=False)
        return HttpPaginatedResponse.http_paginated_response_with_request(http, req)

    @staticmethod
    def http_paginated_response_with_request(http, request):
        response = http.request(request)

        items, content_type, first_rel_request, next_rel_request = \
                PaginatedResult.process_paginated_query_response(request, response)

        return HttpPaginatedResponse(http, items, content_type, first_rel_request,
                                     next_rel_request, response)

