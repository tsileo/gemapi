from urllib.parse import ParseResult


class Request:
    def __init__(
        self,
        parsed_url: ParseResult,
        client_host: str,
        client_port: int,
    ) -> None:
        self.parsed_url = parsed_url
        self.client_host = client_host
        self.client_port = client_port

    @property
    def hostname(self) -> str:
        return self.parsed_url.netloc

    @property
    def path(self) -> str:
        return self.parsed_url.path

    @property
    def query(self) -> str:
        return self.parsed_url.query


class Input:
    def __init__(self, value: str | None = None) -> None:
        self._value: str | None = value

    def get_value(self) -> str:
        if self._value is None:
            raise ValueError("Uninitialized input")
        return self._value


class SensitiveInput(Input):
    pass
