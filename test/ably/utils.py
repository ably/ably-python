
import unittest
import json
from functools import wraps

import msgpack
import mock
import responses

from ably.http.http import Http


class BaseTestCase(unittest.TestCase):

    def responses_add_empty_msg_pack(self, url, method=responses.GET):
        responses.add(responses.GET, url, body=msgpack.packb({}),
                      content_type='application/x-msgpack')

    def protocol_channel_name(self, name):
        return name + ('_bin' if self.use_binary_protocol else '_text')


def assert_responses_type(protocol):
    """
    This is a decorator to check if we retrieved responses with the correct protocol.
    usage:

    @assert_responses_type('json')
    def test_something(self):
        ...

    this will check if all responses received during the test will be in the format
    json.
    supports json and msgpack
    """
    responses = []

    def patch():
        original = Http.make_request

        def fake_make_request(self, *args, **kwargs):
            response = original(self, *args, **kwargs)
            responses.append(response)
            return response

        patcher = mock.patch.object(Http, 'make_request', fake_make_request)
        patcher.start()
        return patcher

    def unpatch(patcher):
        patcher.stop()

    def test_decorator(fn):
        @wraps(fn)
        def test_decorated(self, *args, **kwargs):
            patcher = patch()
            fn(self, *args, **kwargs)
            unpatch(patcher)
            self.assertGreaterEqual(len(responses), 1,
                                    "If your test doesn't make any requests,"
                                    " use the @dont_vary_protocol decorator")
            for response in responses:
                if protocol == 'json':
                    self.assertEquals(response.headers['content-type'], 'application/json')
                    json.loads(response.text)
                else:
                    self.assertEquals(response.headers['content-type'], 'application/x-msgpack')
                    if response.content:
                        msgpack.unpackb(response.content, encoding='utf-8')

        return test_decorated
    return test_decorator


class VaryByProtocolTestsMetaclass(type):
    """
    Metaclass to run tests in more than one protocol.
    Usage:
        * set this as metaclass of the TestCase class
        * create the following method:
        def per_protocol_setup(self, use_binary_protocol):
            # do something here that will run before each test.
        * now every test will run twice and before test is run per_protocol_setup
          is called
        * exclude tests with the @dont_vary_protocol decorator
    """
    def __new__(cls, clsname, bases, dct):
        for key, value in tuple(dct.items()):
            if key.startswith('test') and not getattr(value, 'dont_vary_protocol',
                                                      False):

                wrapper_bin = cls.wrap_as('bin', key, value)
                wrapper_text = cls.wrap_as('text', key, value)

                dct[key + '_bin'] = wrapper_bin
                dct[key + '_text'] = wrapper_text
                del dct[key]

        return super(VaryByProtocolTestsMetaclass, cls).__new__(cls, clsname,
                                                                bases, dct)

    @staticmethod
    def wrap_as(ttype, old_name, old_func):
        expected_content = {'bin': 'msgpack', 'text': 'json'}

        @assert_responses_type(expected_content[ttype])
        def wrapper(self):
            if hasattr(self, 'per_protocol_setup'):
                self.per_protocol_setup(ttype == 'bin')
            old_func(self)
        wrapper.__name__ = old_name + '_' + ttype
        return wrapper


def dont_vary_protocol(func):
    func.dont_vary_protocol = True
    return func
