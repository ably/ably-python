class Message(object):
    def __init__(self, name=None, data=None, client_id=None):
        self.name = name
        self.client_id = client_id
        self.data = data
