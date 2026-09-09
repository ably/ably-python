import warnings

from ably import AblyRealtime, AblyRest
from ably.util.deprecation import suppress_constructor_deprecation
from test.ably.utils import BaseAsyncTestCase


def constructor_warnings(construct):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        construct()
    return [w for w in caught if issubclass(w.category, DeprecationWarning)]


class TestConstructorDeprecation(BaseAsyncTestCase):

    def test_rest_constructor_points_at_the_server_package(self):
        warned = constructor_warnings(lambda: AblyRest(token='foo'))
        assert len(warned) == 1
        message = str(warned[0].message)
        assert AblyRest.__name__ in message
        assert 'create_http_client' in message
        assert 'ably-pubsub-server' in message

    # AblyRealtime delegates to AblyRest, which must not warn a second time
    def test_realtime_constructor_warns_once(self):
        warned = constructor_warnings(lambda: AblyRealtime(token='foo', auto_connect=False))
        assert len(warned) == 1
        message = str(warned[0].message)
        assert 'AblyRealtime' in message
        assert 'create_realtime_client' in message
        assert 'ably-pubsub-server' in message

    def test_the_warning_is_attributed_to_the_calling_code(self):
        warned = constructor_warnings(lambda: AblyRest(token='foo'))
        assert warned[0].filename == __file__

    def test_suppression_silences_the_warning(self):
        with suppress_constructor_deprecation():
            assert constructor_warnings(lambda: AblyRest(token='foo')) == []

    def test_suppression_is_restored_after_the_block(self):
        with suppress_constructor_deprecation():
            AblyRest(token='foo')
        assert len(constructor_warnings(lambda: AblyRest(token='foo'))) == 1

    def test_suppression_is_restored_after_a_failure(self):
        try:
            with suppress_constructor_deprecation():
                raise RuntimeError('boom')
        except RuntimeError:
            pass
        assert len(constructor_warnings(lambda: AblyRest(token='foo'))) == 1
