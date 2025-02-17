import pytest

from ably.types.options import Options


def test_options_should_fail_early_with_incompatible_client_options():
    with pytest.raises(ValueError):
        Options(endpoint="foo", environment="foo")

    with pytest.raises(ValueError):
        Options(endpoint="foo", rest_host="foo")

    with pytest.raises(ValueError):
        Options(endpoint="foo", realtime_host="foo")


# REC1a
def test_options_should_return_the_default_hostnames():
    opts = Options()
    assert opts.get_realtime_host() == "main.realtime.ably.net"
    assert "main.a.fallback.ably-realtime.com" in opts.get_fallback_realtime_hosts()


# REC1b4
def test_options_should_return_the_correct_routing_policy_hostnames():
    opts = Options(endpoint="foo")
    assert opts.get_realtime_host() == "foo.realtime.ably.net"
    assert "foo.a.fallback.ably-realtime.com" in opts.get_fallback_realtime_hosts()


# REC1b3
def test_options_should_return_the_correct_nonprod_routing_policy_hostnames():
    opts = Options(endpoint="nonprod:foo")
    assert opts.get_realtime_host() == "foo.realtime.ably-nonprod.net"
    assert "foo.a.fallback.ably-realtime-nonprod.com" in opts.get_fallback_realtime_hosts()


# REC1b2
def test_options_should_return_the_correct_fqdn_hostnames():
    opts = Options(endpoint="foo.com")
    assert opts.get_realtime_host() == "foo.com"
    assert not opts.get_fallback_realtime_hosts()


# REC1b2
def test_options_should_return_an_ipv4_address():
    opts = Options(endpoint="127.0.0.1")
    assert opts.get_realtime_host() == "127.0.0.1"
    assert not opts.get_fallback_realtime_hosts()


# REC1b2
def test_options_should_return_an_ipv6_address():
    opts = Options(endpoint="::1")
    assert opts.get_realtime_host() == "::1"


# REC1b2
def test_options_should_return_localhost():
    opts = Options(endpoint="localhost")
    assert opts.get_realtime_host() == "localhost"
