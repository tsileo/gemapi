from urllib.parse import ParseResult


class Request:
    def __init__(self, parsed_url: ParseResult) -> None:
        self.parsed_url = parsed_url


class Input:
    def __init__(self, value: str | None = None) -> None:
        self._value: str | None = value

    def get_value(self) -> str:
        if self._value is None:
            raise ValueError("Uninitialized input")
        return self._value
