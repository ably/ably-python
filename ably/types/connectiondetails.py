from dataclasses import dataclass


@dataclass()
class ConnectionDetails:
    connection_state_ttl: int
    max_idle_interval: int
    connection_key: str

    def __init__(self, connection_state_ttl: int, max_idle_interval: int,
                 connection_key: str):
        self.connection_state_ttl = connection_state_ttl
        self.max_idle_interval = max_idle_interval
        self.connection_key = connection_key

    @staticmethod
    def from_dict(json_dict: dict):
        return ConnectionDetails(json_dict.get('connectionStateTtl'), json_dict.get('maxIdleInterval'),
                                 json_dict.get('connectionKey'))
