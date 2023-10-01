from ably.executer.decorator import force_sync
from ably.http.http import Http


class HttpSync(Http):
    @force_sync
    async def close(self):
        await super().close()

    @force_sync
    async def make_request(self, method, path, version=None, headers=None, body=None,
                           skip_auth=False, timeout=None, raise_on_error=True):
        return await super().make_request(method, path, version=version, headers=headers, body=body,
                                          skip_auth=skip_auth, timeout=timeout, raise_on_error=raise_on_error)

    @force_sync
    async def delete(self, url, headers=None, skip_auth=False, timeout=None):
        return await super().delete(url, headers, skip_auth, timeout)

    @force_sync
    async def get(self, url, headers=None, skip_auth=False, timeout=None):
        return await super().get(url, headers, skip_auth, timeout)

    @force_sync
    async def patch(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return await super().patch(url, headers, body, skip_auth, timeout)

    @force_sync
    async def post(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return await super().post(url, headers, body, skip_auth, timeout)

    @force_sync
    async def put(self, url, headers=None, body=None, skip_auth=False, timeout=None):
        return await super().put(url, headers, body, skip_auth, timeout)
