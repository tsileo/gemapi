import asyncio
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from gemapi.request import Input
from gemapi.request import Request
from gemapi.router import Router


class RawResponse:
    def __init__(self, status_code: int, meta: str, content: str | None) -> None:
        self.status_code = status_code
        self.meta = meta
        self.content = content


class Application:
    def __init__(self) -> None:
        self.router = Router()

    def route(self, path: str):
        def _decorator(handler):
            self.router.register_route(path, handler)
            return handler

        return _decorator

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
        matched_route, matched_params = self.router.match(req.parsed_url.path)
        if not matched_route:
            resp = RawResponse(status_code=51, meta="Not found", content=None)
        else:
            if matched_params is None:
                raise ValueError("Missing matched params")

            handler_params: dict[str, Any] = {}
            handler_params.update(matched_params)
            if matched_route.input_parameter and not parsed_url.query:
                resp = RawResponse(
                    status_code=10,
                    meta=matched_route.input_parameter.name,
                    content=None,
                )
            else:
                if matched_route.input_parameter:
                    handler_params[matched_route.input_parameter.name] = Input(
                        parsed_url.query
                    )
                # TODO: pass the path params wit the right type as kwargs
                if matched_route.handler_is_coroutine:
                    resp = await matched_route.handler(req, **handler_params)
                else:
                    resp = matched_route.handler(req, **handler_params)

        data = f"{resp.status_code} {resp.meta}\r\n".encode("utf-8")
        writer.write(data)
        if resp.content:
            writer.write(resp.content.encode())

        await writer.drain()

        logger.info("Close the connection")
        writer.close()

        return
