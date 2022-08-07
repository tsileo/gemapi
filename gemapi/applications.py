import asyncio
import inspect
import re
import ssl
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable
from urllib.parse import ParseResult
from urllib.parse import urlparse

from loguru import logger

_PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class PathParamMatcher(Enum):
    STR = "str"


_PATH_PARAM_MATCHERS = {
    PathParamMatcher.STR: "[^/]+",
}


@dataclass(frozen=True)
class PathParam:
    name: str
    matcher: PathParamMatcher


@dataclass(frozen=True)
class Route:
    path_regex: re.Pattern
    path_params: list[PathParam]
    handler_signature: inspect.Signature
    input_parameter: inspect.Parameter | None
    handler: Callable[..., Any]
    handler_is_coroutine: bool


def _build_path_regex(path: str) -> tuple[re.Pattern, list[PathParam]]:
    # TODO: detect duplicate params and error on invalid matcher
    path_params = []

    replacements = []
    for matched_param in _PARAM_REGEX.finditer(path):
        matcher = PathParamMatcher.STR
        group = matched_param.group()
        parts = group.split(":")

        match parts:
            case [param_name]:
                name = param_name[1:-1]
            case [raw_name, raw_matcher]:
                name = raw_name[1:]
                matcher = PathParamMatcher(raw_matcher[:-1])
            case _:
                raise ValueError(f"Unexpected parts {parts}")

        matcher_regex = _PATH_PARAM_MATCHERS[matcher]
        replacements.append((group, f"(?P<{name}>{matcher_regex})"))
        path_params.append(PathParam(name=name, matcher=matcher))

    for group, replacement in replacements:
        path = path.replace(group, replacement)
    return re.compile(path + "$"), path_params


class Request:
    def __init__(self, parsed_url: ParseResult) -> None:
        self.parsed_url = parsed_url


class RawResponse:
    def __init__(self, status_code: int, meta: str, content: str | None) -> None:
        self.status_code = status_code
        self.meta = meta
        self.content = content


class Input:
    def __init__(self, value: str | None = None) -> None:
        self._value: str | None = value

    def get_value(self) -> str:
        if self._value is None:
            raise ValueError("Uninitialized input")
        return self._value


class Application:
    def __init__(self) -> None:
        self._routes: list[Route] = []

    def route(self, path: str):
        def _decorator(func):
            # TODO: inspect.get_annotations to ensure path params are function
            # parameters
            path_regex, path_params = _build_path_regex(path)
            func_sig = inspect.signature(func)
            maybe_input_param: Input | None = None
            for path_param in path_params:
                if path_param.name not in func_sig.parameters:
                    raise ValueError(
                        f"{func.__name__} is missing a {path_param.name} " "parameter"
                    )
            for param in func_sig.parameters.values():
                if param.annotation is Input:
                    if maybe_input_param is None:
                        maybe_input_param = param
                    else:
                        raise ValueError(
                            f"{func.__name__}: Only 1 Input parameter is allowed"
                        )

            self._routes.append(
                Route(
                    path_regex=path_regex,
                    path_params=path_params,
                    handler_signature=func_sig,
                    input_parameter=maybe_input_param,
                    handler=func,
                    handler_is_coroutine=inspect.iscoroutinefunction(func),
                )
            )
            return func

        return _decorator

    def _get_ssl_ctx(self) -> ssl.SSLContext:
        # Only allow TLS 1.3
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.options |= (
            ssl.OP_NO_SSLv2
            & ssl.OP_NO_SSLv3
            & ssl.OP_NO_TLSv1
            & ssl.OP_NO_TLSv1_1
            & ssl.OP_NO_TLSv1_2
        )
        ssl_ctx.load_cert_chain("cert.pem", keyfile="key.pem")
        return ssl_ctx

    async def stream_handler(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(1024)
        logger.info(data)

        peername = writer.get_extra_info("peername")
        logger.info(f"{peername=}")

        ssl_obj = writer.get_extra_info("ssl_object")
        logger.info(f"{ssl_obj=}")

        logger.info(f"{ssl_obj.server_hostname=}")

        # Ensure it's a valid request
        # 'gemini://localhost/\r\n'
        # 1. ending with a <CR><LF>
        if not data.endswith(b"\r\n"):
            raise ValueError("Not ending with a CRLF")

        message = data.decode()
        parsed_url = urlparse(message[:-2])
        logger.info(f"{parsed_url}")

        if parsed_url.scheme != "gemini":
            raise ValueError("Not a gemini URL")

        req = Request(parsed_url=parsed_url)
        matched = False
        for route in self._routes:
            if m := route.path_regex.match(parsed_url.path):
                matched = True
                logger.info(f"found route {route.handler.__name__}: match={m}")

                if route.input_parameter and not parsed_url.query:
                    resp = RawResponse(
                        status_code=10,
                        meta=route.input_parameter.name,
                        content=None,
                    )
                else:
                    params = m.groupdict()
                    if route.input_parameter:
                        params[route.input_parameter.name] = Input(parsed_url.query)
                    # TODO: pass the path params wit the right type as kwargs
                    if route.handler_is_coroutine:
                        resp = await route.handler(req, **params)
                    else:
                        resp = route.handler(req, **params)

        if matched is False:
            resp = RawResponse(status_code=51, meta="Not found", content=None)

        data = f"{resp.status_code} {resp.meta}\r\n".encode("utf-8")
        writer.write(data)
        if resp.content:
            writer.write(resp.content.encode())

        await writer.drain()

        logger.info("Close the connection")
        writer.close()

        return
