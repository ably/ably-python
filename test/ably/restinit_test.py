from __future__ import absolute_import

import unittest
import logging

from ably import AblyRest
from ably import AblyException
from ably import Options
from ably.transport.defaults import Defaults
from ably.types.fallback import Fallback
from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()


class TestRestInit(unittest.TestCase):
    def test_key_only(self):
        AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))

    def test_key_in_options(self):
        AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))

    def test_specified_host(self):
        ably = AblyRest(Options(restHost="some.other.host", keyId="keyId", keyValue="keyValue"))
        self.assertEqual("some.other.host", ably.options.restHost, 
                msg="Unexpected host mismatch")

    def test_specified_port(self):
        ably = AblyRest(Options(port=9998, tls_port=9999))
        self.assertEqual(9999, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch. Expected: 9999. Actual: %d" % ably.options.tls_port)

    def test_tls_defaults_to_true(self):
        ably = AblyRest(key="some:key")
        self.assertTrue(ably.options.tls,
                msg="Expected encryption to default to true")
        self.assertEqual(Defaults.tls_port, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch")

    def test_tls_can_be_disabled(self):
        options=RestSetup.testOptions()
        options.tls=False
        ably = AblyRest(options)
        self.assertFalse(ably.options.tls,
                msg="Expected encryption to be False")
        self.assertEqual(Defaults.port, Defaults.get_port(ably.options),
                msg="Unexpected port mismatch")

    def test_logger(self):
        #TODO finish
        ably=AblyRest(Options.with_key(test_vars["keys"][0]["key_str"]))
        #ably.setLogLevel(logging.WARNING)

    def test_get_auth(self):
        ably= AblyRest(RestSetup.testOptions())
        auth = ably.auth
        self.assertTrue(auth is not None)

    def test_no_means_throws(self):
        try:
            with self.assertRaises(AblyException) as cm:
                ably= AblyRest()
        except Exception as e:
            log.debug('test_no_means_throws: ablyRest constructor not throwing on no args')
            raise(e)

        optionsWithoutKey= Options()
        try:
            with self.assertRaises(AblyException) as cm:
                ably= AblyRest(optionsWithoutKey)
        except Exception as e:
            log.debug('test_no_means_throws: ablyRest constructor not throwing on no args')
            raise(e)
        
        #these don't throw
        goodAbly=AblyRest(key="some:key")
        anotherGoodAbly=AblyRest(token="some token")

    def test_environment_option(self):
        options = RestSetup.testOptions()
        options.environment = "testEnv"
        options.restHost="another.host.com"

        resolvedHost = Defaults.get_host(options)
        self.assertEqual(resolvedHost, "testEnv-another.host.com")


    def test_get_random_fallback_host(self):
        hosts =["one", "two", "three"]
        fb = Fallback(hosts)
        set_of_hosts= set(hosts)
        h1 = fb.random_host()
        h2= fb.random_host()
        h3 = fb.random_host()
        self.assertEqual(fb.random_host(), None) #all hosts used
        self.assertFalse(h1 == h2)
        self.assertFalse(h1 == h3)
        self.assertFalse(h2 == h3)
        self.assertTrue(h1 in set_of_hosts)
        self.assertTrue(h2 in set_of_hosts)
        self.assertTrue(h3 in set_of_hosts)








