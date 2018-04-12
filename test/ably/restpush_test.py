import string

import pytest
import six

from ably import AblyRest, AblyException, DeviceDetails
from ably.http.paginatedresult import PaginatedResult

from test.ably.restsetup import RestSetup
from test.ably.utils import VaryByProtocolTestsMetaclass, BaseTestCase
from test.ably.utils import new_dict, random_string

test_vars = RestSetup.get_test_vars()


@six.add_metaclass(VaryByProtocolTestsMetaclass)
class TestPush(BaseTestCase):

    def setUp(self):
        self.ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                             rest_host=test_vars["host"],
                             port=test_vars["port"],
                             tls_port=test_vars["tls_port"],
                             tls=test_vars["tls"])

    def per_protocol_setup(self, use_binary_protocol):
        self.ably.options.use_binary_protocol = use_binary_protocol

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

        # Save
        device_id = random_string(26, string.ascii_uppercase + string.digits)
        data = {
            'id': device_id,
            'platform': 'ios',
            'formFactor': 'phone',
            'push': {
                'recipient': {
                    'transportType': 'apns',
                    'deviceToken': '740f4707bebcf74f9b7c25d48e3358945f6aa01da5ddb387462c7eaf61bb78ad'
                }
            },
            'deviceSecret': random_string(12),
        }
        self.ably.push.admin.device_registrations.save(data)

        # Found
        device_details = get(device_id)
        assert type(device_details) is DeviceDetails
        assert device_details.id == device_id
        assert device_details.platform == data['platform']
        assert device_details.form_factor == data['formFactor']
        assert device_details.device_secret == data['deviceSecret']

    # RSH1b2
    def test_admin_device_registrations_list(self):
        datas = []
        for i in range(10):
            device_id = random_string(26, string.ascii_uppercase + string.digits)
            client_id = random_string(12)
            data = {
                'id': device_id,
                'clientId': client_id,
                'platform': 'ios',
                'formFactor': 'phone',
                'push': {
                    'recipient': {
                        'transportType': 'apns',
                        'deviceToken': '740f4707bebcf74f9b7c25d48e3358945f6aa01da5ddb387462c7eaf61bb78ad'
                    }
                },
                'deviceSecret': random_string(12),
            }
            self.ably.push.admin.device_registrations.save(data)
            datas.append(data)

        response = self.ably.push.admin.device_registrations.list()
        assert type(response) is PaginatedResult
        assert type(response.items) is list
        assert type(response.items[0]) is DeviceDetails

        # limit
        response = self.ably.push.admin.device_registrations.list(limit=2)
        assert len(response.items) == 2

        # Filter by device id
        first = datas[0]
        response = self.ably.push.admin.device_registrations.list(deviceId=first['id'])
        assert len(response.items) == 1
        response = self.ably.push.admin.device_registrations.list(
            deviceId=random_string(26, string.ascii_uppercase + string.digits))
        assert len(response.items) == 0

        # Filter by client id
        response = self.ably.push.admin.device_registrations.list(clientId=first['clientId'])
        assert len(response.items) == 1
        response = self.ably.push.admin.device_registrations.list(clientId=random_string(12))
        assert len(response.items) == 0

    # RSH1b3
    def test_admin_device_registrations_save(self):
        save = self.ably.push.admin.device_registrations.save

        device_id = random_string(26, string.ascii_uppercase + string.digits)
        data = {
            'id': device_id,
            'platform': 'ios',
            'formFactor': 'phone',
            'push': {
                'recipient': {
                    'transportType': 'apns',
                    'deviceToken': '740f4707bebcf74f9b7c25d48e3358945f6aa01da5ddb387462c7eaf61bb78ad'
                }
            },
            'deviceSecret': random_string(12),
        }

        # Create
        device_details = save(data)
        assert type(device_details) is DeviceDetails

        # Update
        save(new_dict(data, formFactor='tablet'))

        # Invalid values
        with pytest.raises(ValueError):
            save(new_dict(data, push={'recipient': new_dict(data['push']['recipient'], transportType='xyz')}))
        with pytest.raises(ValueError):
            save(new_dict(data, platform='native'))
        with pytest.raises(ValueError):
            save(new_dict(data, formFactor='fridge'))

        # Fail
        with pytest.raises(AblyException):
            save(new_dict(data, deviceSecret=random_string(12)))
