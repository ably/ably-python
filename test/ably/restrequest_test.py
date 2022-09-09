"""RSC19"""
from test.ably.utils import get_channel_name

import httpx
import pytest
import pytest_asyncio

from ably import AblyRest
from ably.http.paginatedresult import HttpPaginatedResponse


@pytest.fixture(name="channel")
def channel_fixture():
    yield get_channel_name()


@pytest.fixture(name="path")
def path_fixture(channel):
    yield f'/channels/{channel}/messages'


@pytest_asyncio.fixture()
async def setup(rest, path):
    for i in range(20):
        body = {'name': 'event%s' % i, 'data': 'lorem ipsum %s' % i}
        await rest.request('POST', path, body=body)


@pytest.mark.asyncio
async def test_post(path, rest, channel):
    body = {'name': 'test-post', 'data': 'lorem ipsum'}
    result = await rest.request('POST', path, body=body)

    assert isinstance(result, HttpPaginatedResponse)  # RSC19d
    # HP3
    assert type(result.items) is list
    assert len(result.items) == 1
    assert result.items[0]['channel'] == channel
    assert 'messageId' in result.items[0]


@pytest.mark.asyncio
@pytest.mark.usefixtures("setup")
async def test_get(rest, path):
    params = {'limit': 10, 'direction': 'forwards'}
    result = await rest.request('GET', path, params=params)

    assert isinstance(result, HttpPaginatedResponse)  # RSC19d

    # HP2
    assert isinstance(await result.next(), HttpPaginatedResponse)
    assert isinstance(await result.first(), HttpPaginatedResponse)

    # HP3
    assert isinstance(result.items, list)
    item = result.items[0]
    assert isinstance(item, dict)
    assert 'timestamp' in item
    assert 'id' in item
    assert item['name'] == 'event0'
    assert item['data'] == 'lorem ipsum 0'

    assert result.status_code == 200     # HP4
    assert result.success is True        # HP5
    assert result.error_code is None     # HP6
    assert result.error_message is None  # HP7
    assert isinstance(result.headers, list)   # HP7


@pytest.mark.asyncio
async def test_not_found(rest):
    result = await rest.request('GET', '/not-found')
    assert isinstance(result, HttpPaginatedResponse)  # RSC19d
    assert result.status_code == 404             # HP4
    assert result.success is False               # HP5


@pytest.mark.asyncio
async def test_error(rest, path):
    params = {'limit': 'abc'}
    result = await rest.request('GET', path, params=params)
    assert isinstance(result, HttpPaginatedResponse)  # RSC19d
    assert result.status_code == 400  # HP4
    assert not result.success
    assert result.error_code
    assert result.error_message


@pytest.mark.asyncio
async def test_headers(rest):
    key = 'X-Test'
    value = 'lorem ipsum'
    result = await rest.request('GET', '/time', headers={key: value})
    assert result.response.request.headers[key] == value


# RSC19e
@pytest.mark.asyncio
async def test_timeout(test_vars):
    # Timeout
    timeout = 0.000001
    ably = AblyRest(token="foo", http_request_timeout=timeout)
    assert ably.http.http_request_timeout == timeout
    with pytest.raises(httpx.ReadTimeout):
        await ably.request('GET', '/time')
    await ably.close()

    # Bad host, use fallback
    ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                    rest_host='some.other.host',
                    port=test_vars["port"],
                    tls_port=test_vars["tls_port"],
                    tls=test_vars["tls"],
                    fallback_hosts_use_default=True)
    result = await ably.request('GET', '/time')
    assert isinstance(result, HttpPaginatedResponse)
    assert len(result.items) == 1
    assert isinstance(result.items[0], int)
    await ably.close()

    # Bad host, no Fallback
    ably = AblyRest(key=test_vars["keys"][0]["key_str"],
                    rest_host='some.other.host',
                    port=test_vars["port"],
                    tls_port=test_vars["tls_port"],
                    tls=test_vars["tls"])
    with pytest.raises(httpx.ConnectError):
        await ably.request('GET', '/time')
    await ably.close()
