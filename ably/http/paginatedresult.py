from __future__ import absolute_import

import logging

from ably.http.http import Request

log = logging.getLogger(__name__)

class PaginatedResult(object):
    def __init__(self, http, current, content_type, rel_first, rel_current, rel_next, response_processor):
        self.__http = http
        self.__current = current
        self.__content_type = content_type
        self.__rel_first = rel_first
        self.__rel_current = rel_current
        self.__rel_next = rel_next
        self.__response_processor = response_processor

    @property
    def has_first(self):
        return self.__rel_first is not None

    @property
    def current(self):
        return self.__current

    @property
    def has_current(self):
        return self.__rel_current is not None

    @property
    def has_next(self):
        return self.__rel_next is not None

    def get_first(self):
        return self.__get_rel(self.__rel_first)

    def get_current(self):
        return self.__get_rel(self.__rel_current)

    def get_next(self):
        return self.__get_rel(self.__rel_next)

    def __get_rel(self, rel_req):
        if rel_req is None:
            return None
        return PaginatedResult.paginated_query_with_request(self.__http, rel_req, self.__response_processor)

    @staticmethod
    def paginated_query(http, url, headers, response_processor):
        req = Request(method='GET', url=url, headers=headers, body=None, skip_auth=True)
        return PaginatedResult.paginated_query_with_request(http, req, response_processor)

    @staticmethod
    def paginated_query_with_request(http, request, response_processor):
        response = http.request(request)

        current_val = response_processor(response)

        content_type = response.content_type
        links = response.links
        log.debug("Links: %s" % links)
        log.debug("Response: %s" % response)
        if 'first' in links:
            first_rel_request = request.with_relative_url(links['first']['url'])
        else:
            first_rel_request = None

        if 'current' in links:
            current_rel_request = request.with_relative_url(links['current']['url'])
        else:
            current_rel_request = None

        if 'next' in links:
            log.debug("Next: %s" % links['next']['url'])
            next_rel_request = request.with_relative_url(links['next']['url'])
            log.debug("Next rel request: %s" % next_rel_request)
        else:
            next_rel_request = None

        return PaginatedResult(http, current_val, content_type, first_rel_request, current_rel_request, next_rel_request, response_processor)
