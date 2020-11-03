import itertools
import random
import string
import time

import pytest

from ably import AblyException, AblyAuthException
from ably import DeviceDetails, PushChannelSubscription
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, BaseTestCase
from test.ably.utils import new_dict, random_string, get_random_key


DEVICE_TOKEN = '740f4707bebcf74f9b7c25d48e3358945f6aa01da5ddb387462c7eaf61bb78ad'


class TestPush(BaseTestCase, metaclass=VaryByProtocolTestsMetaclass):

    @classmethod
    def setUpClass(cls):
        cls.ably = RestSetup.get_ably_rest()

        # Register several devices for later use
        cls.devices = {}
        for i in range(10):
            cls.save_device()

        # Register several subscriptions for later use
        cls.channels = {'canpublish:test1': [], 'canpublish:test2': [], 'canpublish:test3': []}
        for key, channel in zip(cls.devices, itertools.cycle(cls.channels)):
            device = cls.devices[key]
            cls.save_subscription(channel, device_id=device.id)
        assert len(list(itertools.chain(*cls.channels.values()))) == len(cls.devices)

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol

    @classmethod
    def get_client_id(cls):
        return random_string(12)

    @classmethod
    def get_device_id(cls):
        return random_string(26, string.ascii_uppercase + string.digits)

    @classmethod
    def gen_device_data(cls, data=None, **kw):
        if data is None:
            data = {
                'id': cls.get_device_id(),
                'clientId': cls.get_client_id(),
                'platform': random.choice(['android', 'ios']),
                'formFactor': 'phone',
                'push': {
                    'recipient': {
                        'transportType': 'apns',
                        'deviceToken': DEVICE_TOKEN,
                    }
                },
            }
        else:
            data = data.copy()

        data.update(kw)
        return data

    @classmethod
    def save_device(cls, data=None, **kw):
        """
        Helper method to register a device, to not have this code repeated
        everywhere. Returns the input dict that was sent to Ably, and the
        device details returned by Ably.
        """
        data = cls.gen_device_data(data, **kw)
        device = cls.ably.push.admin.device_registrations.save(data)
        cls.devices[device.id] = device
        return device

    @classmethod
    def remove_device(cls, device_id):
        result = cls.ably.push.admin.device_registrations.remove(device_id)
        cls.devices.pop(device_id, None)
        return result

    @classmethod
    def remove_device_where(cls, **kw):
        remove_where = cls.ably.push.admin.device_registrations.remove_where
        result = remove_where(**kw)

        aux = {'deviceId': 'id', 'clientId': 'client_id'}
        for device in list(cls.devices.values()):
            for key, value in kw.items():
                key = aux[key]
                if getattr(device, key) == value:
                    del cls.devices[device.id]

        return result

    @classmethod
    def get_device(cls):
        key = get_random_key(cls.devices)
        return cls.devices[key]

    @classmethod
    def get_channel(cls):
        key = get_random_key(cls.channels)
        return key, cls.channels[key]

    @classmethod
    def save_subscription(cls, channel, **kw):
        """
        Helper method to register a device, to not have this code repeated
        everywhere. Returns the input dict that was sent to Ably, and the
        device details returned by Ably.
        """
        subscription = PushChannelSubscription(channel, **kw)
        subscription = cls.ably.push.admin.channel_subscriptions.save(subscription)
        cls.channels.setdefault(channel, []).append(subscription)
        return subscription

    # RSH1a
    def test_admin_publish(self):
        recipient = {'clientId': 'ablyChannel'}
        data = {
            'data': {'foo': 'bar'},
        }

        publish = self.ably.push.admin.publish
        with pytest.raises(TypeError):
            publish('ablyChannel', data)
        with pytest.raises(TypeError):
            publish(recipient, 25)
        with pytest.raises(ValueError):
            publish({}, data)
        with pytest.raises(ValueError):
            publish(recipient, {})

        with pytest.raises(AblyException):
            publish(recipient, {'xxx': 5})

        assert publish(recipient, data) is None

    # RSH1b1
    def test_admin_device_registrations_get(self):
        get = self.ably.push.admin.device_registrations.get

        # Not found
        with pytest.raises(AblyException):
            get('not-found')

        # Found
        device = self.get_device()
        device_details = get(device.id)
        assert device_details.id == device.id
        assert device_details.platform == device.platform
        assert device_details.form_factor == device.form_factor

    # RSH1b2
    def test_admin_device_registrations_list(self):
        list_devices = self.ably.push.admin.device_registrations.list

        response = list_devices()
        assert type(response) is PaginatedResult
        assert type(response.items) is list
        assert type(response.items[0]) is DeviceDetails

        # limit
        assert len(list_devices(limit=5000).items) == len(self.devices)
        assert len(list_devices(limit=2).items) == 2

        # Filter by device id
        device = self.get_device()
        assert len(list_devices(deviceId=device.id).items) == 1
        assert len(list_devices(deviceId=self.get_device_id()).items) == 0

        # Filter by client id
        assert len(list_devices(clientId=device.client_id).items) == 1
        assert len(list_devices(clientId=self.get_client_id()).items) == 0

    # RSH1b3
    def test_admin_device_registrations_save(self):
        # Create
        data = self.gen_device_data()
        device = self.save_device(data)
        assert type(device) is DeviceDetails

        # Update
        self.save_device(data, formFactor='tablet')

        # Invalid values
        with pytest.raises(ValueError):
            push = {'recipient': new_dict(data['push']['recipient'], transportType='xyz')}
            self.save_device(data, push=push)
        with pytest.raises(ValueError):
            self.save_device(data, platform='native')
        with pytest.raises(ValueError):
            self.save_device(data, formFactor='fridge')

        # Fail
        with pytest.raises(AblyException):
            self.save_device(data, push={'color': 'red'})

    # RSH1b4
    def test_admin_device_registrations_remove(self):
        get = self.ably.push.admin.device_registrations.get

        device = self.get_device()

        # Remove
        assert get(device.id).id == device.id  # Exists
        assert self.remove_device(device.id).status_code == 204
        with pytest.raises(AblyException):  # Doesn't exist
            get(device.id)

        # Remove again, it doesn't fail
        assert self.remove_device(device.id).status_code == 204

    # RSH1b5
    def test_admin_device_registrations_remove_where(self):
        get = self.ably.push.admin.device_registrations.get

        # Remove by device id
        device = self.get_device()
        assert get(device.id).id == device.id  # Exists
        assert self.remove_device_where(deviceId=device.id).status_code == 204
        with pytest.raises(AblyException):  # Doesn't exist
            get(device.id)

        # Remove by client id
        device = self.get_device()
        assert get(device.id).id == device.id  # Exists
        assert self.remove_device_where(clientId=device.client_id).status_code == 204
        # Doesn't exist (Deletion is async: wait up to a few seconds before giving up)
        with pytest.raises(AblyException):
            for i in range(5):
                time.sleep(1)
                get(device.id)

        # Remove with no matching params
        assert self.remove_device_where(clientId=device.client_id).status_code == 204

    # RSH1c1
    def test_admin_channel_subscriptions_list(self):
        list_ = self.ably.push.admin.channel_subscriptions.list

        channel, subscriptions = self.get_channel()

        response = list_(channel=channel)
        assert type(response) is PaginatedResult
        assert type(response.items) is list
        assert type(response.items[0]) is PushChannelSubscription

        # limit
        assert len(list_(channel=channel, limit=5000).items) == len(subscriptions)
        assert len(list_(channel=channel, limit=2).items) == 2

        # Filter by device id
        device_id = subscriptions[0].device_id
        items = list_(channel=channel, deviceId=device_id).items
        assert len(items) == 1
        assert items[0].device_id == device_id
        assert items[0].channel == channel

        assert len(list_(channel=channel, deviceId=self.get_device_id()).items) == 0

        # Filter by client id
        device = self.get_device()
        assert len(list_(channel=channel, clientId=device.client_id).items) == 0

    # RSH1c2
    def test_admin_channels_list(self):
        list_ = self.ably.push.admin.channel_subscriptions.list_channels

        response = list_()
        assert type(response) is PaginatedResult
        assert type(response.items) is list
        assert type(response.items[0]) is str

        # limit
        assert len(list_(limit=5000).items) == len(self.channels)
        assert len(list_(limit=1).items) == 1

    # RSH1c3
    def test_admin_channel_subscriptions_save(self):
        save = self.ably.push.admin.channel_subscriptions.save

        # Subscribe
        device = self.get_device()
        channel = 'canpublish:testsave'
        subscription = self.save_subscription(channel, device_id=device.id)
        assert type(subscription) is PushChannelSubscription
        assert subscription.channel == channel
        assert subscription.device_id == device.id
        assert subscription.client_id is None

        # Failures
        client_id = self.get_client_id()
        with pytest.raises(ValueError):
            PushChannelSubscription(channel, device_id=device.id, client_id=client_id)

        subscription = PushChannelSubscription('notallowed', device_id=device.id)
        with pytest.raises(AblyAuthException):
            save(subscription)

        subscription = PushChannelSubscription(channel, device_id='notregistered')
        with pytest.raises(AblyException):
            save(subscription)

    # RSH1c4
    def test_admin_channel_subscriptions_remove(self):
        save = self.ably.push.admin.channel_subscriptions.save
        remove = self.ably.push.admin.channel_subscriptions.remove
        list_ = self.ably.push.admin.channel_subscriptions.list

        channel = 'canpublish:testremove'

        # Subscribe device
        device = self.get_device()
        subscription = save(PushChannelSubscription(channel, device_id=device.id))
        assert device.id in (x.device_id for x in list_(channel=channel).items)
        assert remove(subscription).status_code == 204
        assert device.id not in (x.device_id for x in list_(channel=channel).items)

        # Subscribe client
        client_id = self.get_client_id()
        subscription = save(PushChannelSubscription(channel, client_id=client_id))
        assert client_id in (x.client_id for x in list_(channel=channel).items)
        assert remove(subscription).status_code == 204
        assert client_id not in (x.client_id for x in list_(channel=channel).items)

        # Remove again, it doesn't fail
        assert remove(subscription).status_code == 204

    # RSH1c5
    def test_admin_channel_subscriptions_remove_where(self):
        save = self.ably.push.admin.channel_subscriptions.save
        remove = self.ably.push.admin.channel_subscriptions.remove_where
        list_ = self.ably.push.admin.channel_subscriptions.list

        channel = 'canpublish:testremovewhere'

        # Subscribe device
        device = self.get_device()
        save(PushChannelSubscription(channel, device_id=device.id))
        assert device.id in (x.device_id for x in list_(channel=channel).items)
        assert remove(channel=channel, device_id=device.id).status_code == 204
        assert device.id not in (x.device_id for x in list_(channel=channel).items)

        # Subscribe client
        client_id = self.get_client_id()
        save(PushChannelSubscription(channel, client_id=client_id))
        assert client_id in (x.client_id for x in list_(channel=channel).items)
        assert remove(channel=channel, client_id=client_id).status_code == 204
        assert client_id not in (x.client_id for x in list_(channel=channel).items)

        # Remove again, it doesn't fail
        assert remove(channel=channel, client_id=client_id).status_code == 204
