import random
import string
import time

import pytest
import six

from ably import AblyRest, AblyException, AblyAuthException
from ably import DeviceDetails, PushChannelSubscription
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, BaseTestCase
from test.ably.utils import new_dict, random_string

test_vars = RestSetup.get_test_vars()


DEVICE_TOKEN = '740f4707bebcf74f9b7c25d48e3358945f6aa01da5ddb387462c7eaf61bb78ad'


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestPush(BaseTestCase):

    @classmethod
    def setUpClass(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

        # Register several devices for later use
        self.devices = {}
        for i in range(10):
            self.save_device()

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol

    @classmethod
    def get_client_id(self):
        return random_string(12)

    @classmethod
    def get_device_id(self):
        return random_string(26, string.ascii_uppercase + string.digits)

    @classmethod
    def gen_device_data(self, data=None, **kw):
        if data is None:
            data = {
                'id': self.get_device_id(),
                'clientId': self.get_client_id(),
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
    def save_device(self, data=None, **kw):
        """
        Helper method to register a device, to not have this code repeated
        everywhere. Returns the input dict that was sent to Ably, and the
        device details returned by Ably.
        """
        data = self.gen_device_data(data, **kw)
        device = self.ably.push.admin.device_registrations.save(data)
        self.devices[device.id] = device
        return device

    @classmethod
    def remove_device(self, device_id):
        result = self.ably.push.admin.device_registrations.remove(device_id)
        self.devices.pop(device_id, None)
        return result

    @classmethod
    def remove_device_where(self, **kw):
        remove_where = self.ably.push.admin.device_registrations.remove_where
        result = remove_where(**kw)

        aux = {'deviceId': 'id', 'clientId': 'client_id'}
        for device in list(self.devices.values()):
            for key, value in kw.items():
                key = aux[key]
                if getattr(device, key) == value:
                    del self.devices[device.id]

        return result

    def get_device(self):
        key = random.choice(list(self.devices.keys()))
        return self.devices[key]

    # RSH1a
    def test_admin_publish(self):
        recipient = {'clientId': 'ablyChannel'}
        data = {
            'data': {'foo': 'bar'},
        }

        publish = self.ably.push.admin.publish
        with pytest.raises(TypeError): publish('ablyChannel', data)
        with pytest.raises(TypeError): publish(recipient, 25)
        with pytest.raises(ValueError): publish({}, data)
        with pytest.raises(ValueError): publish(recipient, {})

        response = publish(recipient, data)
        assert response.status_code == 204

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
        assert get(device.id).id == device.id # Exists
        assert self.remove_device(device.id).status_code == 204
        with pytest.raises(AblyException): get(device.id) # Doesn't exist

        # Remove again, it doesn't fail
        assert self.remove_device(device.id).status_code == 204

    # RSH1b5
    def test_admin_device_registrations_remove_where(self):
        get = self.ably.push.admin.device_registrations.get

        # Remove by device id
        device = self.get_device()
        assert get(device.id).id == device.id # Exists
        assert self.remove_device_where(deviceId=device.id).status_code == 204
        with pytest.raises(AblyException): get(device.id) # Doesn't exist

        # Remove by client id
        device = self.get_device()
        assert get(device.id).id == device.id # Exists
        assert self.remove_device_where(clientId=device.client_id).status_code == 204
        time.sleep(1) # Deletion is async: wait a little bit
        with pytest.raises(AblyException): get(device.id) # Doesn't exist

        # Remove with no matching params
        assert self.remove_device_where(clientId=device.client_id).status_code == 204

    # RSH1c3
    def test_admin_channel_subscriptions_save(self):
        save = self.ably.push.admin.channel_subscriptions.save

        # Register device
        device = self.get_device()

        # Subscribe
        channel = 'canpublish:test'
        subscription = PushChannelSubscription(channel, device_id=device.id)
        subscription = save(subscription)
        assert type(subscription) is PushChannelSubscription
        assert subscription.channel == channel
        assert subscription.device_id == device.id
        assert subscription.client_id is None

        # Update
        channel = 'canpublish:test'
        subscription = PushChannelSubscription(channel, device_id=device.id)
        subscription = save(subscription)
        assert type(subscription) is PushChannelSubscription
        assert subscription.channel == channel
        assert subscription.device_id == device.id
        assert subscription.client_id is None

        # Failures
        client_id = self.get_client_id()
        with pytest.raises(ValueError):
            PushChannelSubscription(channel, device_id=device.id, client_id=client_id)

        subscription = PushChannelSubscription('notallowed', device_id=device.id)
        with pytest.raises(AblyAuthException): save(subscription)

        subscription = PushChannelSubscription(channel, device_id='notregistered')
        with pytest.raises(AblyException): save(subscription)
