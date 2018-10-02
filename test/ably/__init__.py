from requests.adapters import HTTPAdapter

real_send = HTTPAdapter.send
def send(*args, **kw):
    response = real_send(*args, **kw)

    from requests_toolbelt.utils import dump
    data = dump.dump_all(response)
    for line in data.splitlines():
        try:
            line = line.decode('utf-8')
        except UnicodeDecodeError:
            line = bytes(line)
        print(line)

    return response


# Uncomment this to print request/response
# HTTPAdapter.send = send
