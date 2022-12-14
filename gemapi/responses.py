from enum import IntEnum
from typing import ClassVar


class StatusCode(IntEnum):
    INPUT = 10
    SENSITIVE_INPUT = 11

    SUCCESS = 20

    TEMPORARY_REDIRECT = 30
    PERMANENT_REDIRECT = 31

    TEMPORARY_FAILURE = 40
    SERVER_UNAVAILABLE = 41
    CGI_ERROR = 42
    PROXY_ERROR = 43
    SLOW_DOWN = 44

    PERMANENT_FAILURE = 50
    NOT_FOUND = 51
    GONE = 52
    PROXY_REQUEST_REFUSED = 53
    BAD_REQUEST = 59

    CLIENT_CERTIFICATE_REQUIRED = 60
    CERTIFICATE_NOT_AUTHORISED = 61
    CERTIFICATE_NOT_VALID = 62


class Response:
    def __init__(
        self,
        status_code: StatusCode | int,
        meta: str,
        body: str | None = None,
    ) -> None:
        self.status_code = (
            status_code
            if isinstance(status_code, StatusCode)
            else StatusCode(status_code)
        )
        self.meta = meta
        self.body = body

    def as_bytes(self) -> bytes:
        data = f"{self.status_code.value} {self.meta}\r\n"
        if self.body:
            data += self.body

        return data.encode("utf-8")


class StatusError(Exception):

    STATUS_CODE: ClassVar[StatusCode]

    def __init__(self, meta: str) -> None:
        self.meta = meta

    def as_response(self) -> Response:
        return Response(self.STATUS_CODE, self.meta)

    def data(self) -> str:
        return f"{self.STATUS_CODE.name}: {self.STATUS_CODE.value} {self.meta}"


class NotFoundError(StatusError):
    STATUS_CODE = StatusCode.NOT_FOUND


class GoneError(StatusError):
    STATUS_CODE = StatusCode.GONE


class BadRequestError(StatusError):
    STATUS_CODE = StatusCode.BAD_REQUEST


class TemporaryFailureError(StatusError):
    STATUS_CODE = StatusCode.TEMPORARY_FAILURE


class NotFoundResponse(Response):
    def __init__(self, meta: str = "Not found") -> None:
        super().__init__(StatusCode.NOT_FOUND, meta)


class InputResponse(Response):
    def __init__(self, meta: str) -> None:
        super().__init__(StatusCode.INPUT, meta)


class SensitiveInputResponse(Response):
    def __init__(self, meta: str) -> None:
        super().__init__(StatusCode.SENSITIVE_INPUT, meta)


class BadRequestResponse(Response):
    def __init__(self, meta: str) -> None:
        super().__init__(StatusCode.BAD_REQUEST, meta)


class TemporaryFailureResponse(Response):
    def __init__(self, meta: str) -> None:
        super().__init__(StatusCode.TEMPORARY_FAILURE, meta)
