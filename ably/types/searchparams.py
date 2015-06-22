from __future__ import absolute_import
import calendar
from ably.types.authoptions import AuthOptions
from ably.util.exceptions import AblyException
from six.moves.urllib.parse import urlencode

class SearchParams(object):
    class Unit:
        MINUTE="minute"
        HOUR="hour"
        DAY="day"
        MONTH="month"
        
    def __init__(self, backwards=True, start=None, end=None, limit=100,  clientId=None, connection_id=None, unit=None):

        self.direction= "backwards" if backwards else "forwards"
        self.start = self._format_time_param(start) if start else None
        self.end = self._format_time_param(end) if end else None
        self.unit =unit
        if limit > 1000:
            raise AblyException(reason="limit can not be over 1000",
                                status_code=400,
                                code=40000)
        self.limit = "%d" % limit
        self.connection_id = connection_id
        self.clientId = clientId

    def as_dict(self):
        params ={}
        params["direction"] = self.direction
        params["limit"] = self.limit
        if self.start:
            params["start"] = self.start
        if self.end:
            params["end"] = self.end
        if self.connection_id:
            params["connectionId"] = self.connection_id
        if self.clientId:
            params["clientId"] = self.clientId
        if self.unit:
            params["unit"] = self.unit
        return params

    def append_to_url(self, url):
        params = self.as_dict()
        return url + '?' + urlencode(params)
        
    def _format_time_param(self, t):
        try:
            return '%d' % (calendar.timegm(t.utctimetuple()) * 1000)
        except:
            return '%s' % t
