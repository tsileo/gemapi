class Response:
    def __init__(self, status_code: int, meta: str, body: str | None = None) -> None:
        self.status_code = status_code
        self.meta = meta
        self.body = body

    def as_bytes(self) -> bytes:
        data = f"{self.status_code} {self.meta}\r\n"
        if self.body:
            data += self.body

        return data.encode("utf-8")


class NotFoundResponse(Response):
    def __init__(self, meta: str = "Not found") -> None:
        super().__init__(51, meta)


class InputResponse(Response):
    def __init__(self, meta: str) -> None:
        super().__init__(10, meta)
