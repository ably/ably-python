import functools
import os
import random
import string
import unittest
import sys

if sys.version_info >= (3, 8):
    from unittest import IsolatedAsyncioTestCase
else:
    from async_case import IsolatedAsyncioTestCase

import msgpack
import mock
import respx
from httpx import Response

from ably.http.http import Http


class BaseTestCase(unittest.TestCase):

    def respx_add_empty_msg_pack(self, url, method='GET'):
        respx.route(method=method, url=url).return_value = Response(
            status_code=200,
            headers={'content-type': 'application/x-msgpack'},
            content=msgpack.packb({})
        )

    @classmethod
    def get_channel_name(cls, prefix=''):
        return prefix + random_string(10)

    @classmethod
    def get_channel(cls, prefix=''):
        name = cls.get_channel_name(prefix)
        return cls.ably.channels.get(name)


class BaseAsyncTestCase(IsolatedAsyncioTestCase):

    def respx_add_empty_msg_pack(self, url, method='GET'):
        respx.route(method=method, url=url).return_value = Response(
            status_code=200,
            headers={'content-type': 'application/x-msgpack'},
            content=msgpack.packb({})
        )

    @classmethod
    def get_channel_name(cls, prefix=''):
        return prefix + random_string(10)

    def get_channel(self, prefix=''):
        name = self.get_channel_name(prefix)
        return self.ably.channels.get(name)


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

        async def fake_make_request(self, *args, **kwargs):
            response = await original(self, *args, **kwargs)
            responses.append(response)
            return response

        patcher = mock.patch.object(Http, 'make_request', fake_make_request)
        patcher.start()
        return patcher

    def unpatch(patcher):
        patcher.stop()

    def test_decorator(fn):
        @functools.wraps(fn)
        async def test_decorated(self, *args, **kwargs):
            patcher = patch()
            await fn(self, *args, **kwargs)
            unpatch(patcher)

            assert len(responses) >= 1, \
                "If your test doesn't make any requests, use the @dont_vary_protocol decorator"

            for response in responses:
                # In HTTP/2 some header fields are optional in case of 204 status code
                if protocol == 'json':
                    if response.status_code != 204:
                        assert response.headers['content-type'] == 'application/json'
                    if response.content:
                        response.json()
                else:
                    if response.status_code != 204:
                        assert response.headers['content-type'] == 'application/x-msgpack'
                    if response.content:
                        msgpack.unpackb(response.content)

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

        return super().__new__(cls, clsname, bases, dct)

    @staticmethod
    def wrap_as(ttype, old_name, old_func):
        expected_content = {'bin': 'msgpack', 'text': 'json'}

        @assert_responses_type(expected_content[ttype])
        async def wrapper(self):
            if hasattr(self, 'per_protocol_setup'):
                self.per_protocol_setup(ttype == 'bin')
            await old_func(self)

        wrapper.__name__ = old_name + '_' + ttype
        return wrapper


def dont_vary_protocol(func):
    func.dont_vary_protocol = True
    return func


def random_string(length, alphabet=string.ascii_letters):
    return ''.join([random.choice(alphabet) for x in range(length)])


def new_dict(src, **kw):
    new = src.copy()
    new.update(kw)
    return new


def get_random_key(d):
    return random.choice(list(d))


def get_submodule_dir(filepath):
    root_dir = os.path.dirname(filepath)
    while True:
        if os.path.exists(os.path.join(root_dir, 'submodules')):
            return os.path.join(root_dir, 'submodules')
        root_dir = os.path.dirname(root_dir)
