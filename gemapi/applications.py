import asyncio
import re
import ssl
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

from loguru import logger

_PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class PathParamMatcher(Enum):
    STR = "str"


_PATH_PARAM_MATCHERS = {
    PathParamMatcher.STR: "[^/]+",
}


@dataclass
class PathParam:
    name: str
    matcher: PathParamMatcher


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
    pass


class RawResponse:
    def __init__(self, status_code: int, meta: str, content: str) -> None:
        self.status_code = status_code
        self.meta = meta
        self.content = content


class Application:
    def __init__(self) -> None:
        self._routes = []  # type: ignore

    def route(self, path: str):
        def _decorator(func):
            # TODO: inspect.get_annotations to ensure path params are function
            # parameters
            path_regex, path_params = _build_path_regex(path)
            self._routes.append((path_regex, path_params, func))
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

    async def _stream_handler(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(1024)
        logger.info(data)

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

        req = Request()
        matched = False
        for path_regex, _, path_handler in self._routes:
            if m := path_regex.match(parsed_url.path):
                logger.info(f"found route {path_handler.__name__}: match={m}")
                # TODO: pass the path params as kwargs
                resp = await path_handler(req)
                matched = True

        if matched is False:
            raise ValueError("TODO not found")

        data = f"{resp.status_code} {resp.meta}\r\n".encode("utf-8")
        writer.write(data)
        writer.write(resp.content.encode())
        await writer.drain()

        logger.info("Close the connection")
        writer.close()

        return

    async def run(self, host: str = "localhost", port: int = 1965):
        server = await asyncio.start_server(
            self._stream_handler, host, port, ssl=self._get_ssl_ctx()
        )
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        logger.info(f"Serving on {addrs}")

        async with server:
            await server.serve_forever()
