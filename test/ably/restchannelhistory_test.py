from __future__ import absolute_import

import math
from datetime import datetime
from datetime import timedelta
import logging
import time
import unittest

import six
from six.moves import range

from ably import AblyException
from ably import AblyRest
from ably import Options

from test.ably.restsetup import RestSetup

test_vars = RestSetup.get_test_vars()
log = logging.getLogger(__name__)


class TestRestChannelHistory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ably = AblyRest(Options.with_key(test_vars["keys"][0]["key_str"],
                host=test_vars["host"],
                port=test_vars["port"],
                tls_port=test_vars["tls_port"],
                tls=test_vars["tls"]))
        cls.time_offset = cls.ably.time() - int(time.time())

    @property
    def ably(self):
        return TestRestChannelHistory.ably

    def test_channel_history_types(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_types']
        history0.publish('history0', True)
        history0.publish('history1', 24)
        history0.publish('history2', 24.234)
        history0.publish('history3', six.u('This is a string message payload'))
        history0.publish('history4', b'This is a byte[] message payload')
        history0.publish('history5', {'test': 'This is a JSONObject message payload'})
        history0.publish('history6', ['This is a JSONArray message payload'])

        # Wait for the history to be persisted
        time.sleep(16)

        history = history0.history()
        messages = history.current
        self.assertIsNotNone(messages, msg="Expected non-None messages")
        self.assertEquals(7, len(messages), msg="Expected 7 messages")
        
        message_contents = {m.name:m.data for m in messages}

        self.assertEquals(True, message_contents["history0"],
                msg="Expect history0 to be Boolean(true)")
        self.assertEquals(24, int(message_contents["history1"]),
                msg="Expect history1 to be Int(24)")
        self.assertEquals(24.234, float(message_contents["history2"]),
                msg="Expect history2 to be Double(24.234)")
        self.assertEquals(six.u("This is a string message payload"),
                message_contents["history3"],
                msg="Expect history3 to be expected String)")
        self.assertEquals(b"This is a byte[] message payload",
                message_contents["history4"],
                msg="Expect history4 to be expected byte[]")
        self.assertEquals({"test": "This is a JSONObject message payload"},
                message_contents["history5"],
                msg="Expect history5 to be expected JSONObject")
        self.assertEquals(["This is a JSONArray message payload"],
                message_contents["history6"],
                msg="Expect history6 to be expected JSONObject")

        expected_message_history = [
            message_contents['history6'],
            message_contents['history5'],
            message_contents['history4'],
            message_contents['history3'],
            message_contents['history2'],
            message_contents['history1'],
            message_contents['history0'],
        ]

        self.assertEquals(expected_message_history, [m.data for m in messages],
                msg="Expect messages in reverse order")

    def test_channel_history_multi_50_forwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_multi_50_f']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='forwards')
        self.assertIsNotNone(history)
        messages = history.current
        self.assertEquals(50, len(messages),
                msg="Expected 50 messages")

        expected_messages = ['history%d' % i for i in range(50)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in forward order')

    def test_channel_history_multi_50_backwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_multi_50_b']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='backwards')
        self.assertIsNotNone(history)
        messages = history.current
        self.assertEquals(50, len(messages),
                msg="Expected 50 messages")

        expected_messages = ['history%d' % i for i in range(49, -1, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in reverse order')

    def test_channel_history_limit_forwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_limit_f']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='forwards', limit=25)
        self.assertIsNotNone(history)
        messages = history.current
        self.assertEquals(25, len(messages),
                msg="Expected 25 messages")

        expected_messages = ['history%d' % i for i in range(25)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in forward order')

    def test_channel_history_limit_backwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_limit_f']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='backwards', limit=25)
        self.assertIsNotNone(history)
        messages = history.current
        self.assertEquals(25, len(messages),
                msg="Expected 25 messages")

        expected_messages = ['history%d' % i for i in range(49, 24, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in forward order')

    def test_channel_history_time_forwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_time_f']

        for i in range(20):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        interval_start = int(TestRestChannelHistory.time_offset + time.time())

        for i in range(20, 40):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        interval_end = int(TestRestChannelHistory.time_offset + time.time())

        for i in range(40, 60):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        time.sleep(16)

        history = history0.history(direction='forwards', start=interval_start,
                end=interval_end)

        messages = history.current
        self.assertEquals(20, len(messages))

        expected_messages = ['history%d' % i for i in range(20, 40)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in forward order')

    def test_channel_history_time_backwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_time_b']

        for i in range(20):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        interval_start = int(TestRestChannelHistory.time_offset + time.time())

        for i in range(20, 40):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        interval_end = int(TestRestChannelHistory.time_offset + time.time())

        for i in range(40, 60):
            history0.publish('history%d' % i, i)
            time.sleep(0.1)

        time.sleep(16)

        history = history0.history(direction='backwards', start=interval_start,
                end=interval_end)

        messages = history.current
        self.assertEquals(20, len(messages))

        expected_messages = ['history%d' % i for i in range(39, 29, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expect messages in reverse order')

    def test_channel_history_paginate_forwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_paginate_f']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='forwards', limit=10)
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(0, 10)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(10, 20)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(20, 30)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
    def test_channel_history_paginate_backwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_paginate_b']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='backwards', limit=10)
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(49, 39, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(39, 29, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(29, 19, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
    def test_channel_history_paginate_forwards(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_paginate_first_f']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='forwards', limit=10)
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(0, 10)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(10, 20)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_first()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(0, 10)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
    def test_channel_history_paginate_backwards_rel_first(self):
        history0 = TestRestChannelHistory.ably.channels['persisted:channelhistory_paginate_first_b']

        for i in range(50):
            history0.publish('history%d' % i, i)

        time.sleep(16)

        history = history0.history(direction='backwards', limit=10)
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(49, 39, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_next()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(39, 29, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
        
        history = history.get_first()
        messages = history.current

        self.assertEquals(10, len(messages))

        expected_messages = ['history%d' % i for i in range(49, 39, -1)]
        actual_messages = [m.data for m in messages]

        self.assertEquals(expected_messages, actual_messages,
                msg='Expected 10 messages')
