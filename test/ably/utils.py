
import json
from importlib import import_module
from functools import wraps

import msgpack
import mock


TO_MOCK = [
    'ably.types.presence.make_presence_response_handler',
    'ably.types.presence.make_encrypted_presence_response_handler',
    'ably.rest.rest.make_stats_response_processor',
]


def assert_responses_types(types):
    """
    This code is a bit complicated but saves a lot of coding.
    It is a decorator to check if we retrieved presence with the correct protocol.
    usage:

    @assert_responses_types(['json', 'msgpack'])
    def test_something(self):
        ...

    this will check if we receive two responses, the first using json and the
    second msgpack
    """
    responses = []

    def _get_side_effect_that_saves_response(handler_str):
        module = import_module('.'.join(handler_str.split('.')[:-1]))
        old_handler = getattr(module, handler_str.split('.')[-1])

        def side_effect(*args, **kwargs):
            def handler(response):
                responses.append(response)
                return old_handler(*args, **kwargs)(response)
            return handler
        return side_effect

    def patch_handlers():
        patchers = []
        for handler in TO_MOCK:
            patchers.append(mock.patch(
                            handler,
                            _get_side_effect_that_saves_response(handler)))
            patchers[-1].start()
        return patchers

    def unpatch_handlers(patchers):
        for patcher in patchers:
            patcher.stop()

    def test_decorator(fn):
        @wraps(fn)
        def test_decorated(self, *args, **kwargs):
            patchers = patch_handlers()
            fn(self, *args, **kwargs)
            unpatch_handlers(patchers)
            self.assertEquals(len(types), len(responses))
            for type_name, response in zip(types, responses):
                if type_name == 'json':
                    self.assertEquals(response.headers['content-type'], 'application/json')
                    json.loads(response.text)
                else:
                    self.assertEquals(response.headers['content-type'], 'application/x-msgpack')
                    msgpack.unpackb(response.content, encoding='utf-8')

        return test_decorated
    return test_decorator
