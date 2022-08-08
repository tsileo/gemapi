import asyncio
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from gemapi.request import Input
from gemapi.request import Request
from gemapi.request import SensitiveInput
from gemapi.responses import InputResponse
from gemapi.responses import NotFoundResponse
from gemapi.responses import Response
from gemapi.responses import SensitiveInputResponse
from gemapi.router import Router


class Application:
    def __init__(self) -> None:
        self._default_router = Router()
        self._hostnames: dict[str, Router] = {}

    def route(self, path: str):
        return self._default_router.route(path)

    def router_for_hostname(self, hostname: str) -> Router:
        if hostname not in self._hostnames:
            router = Router()
            self._hostnames[hostname] = router
        else:
            router = self._hostnames[hostname]

        return router

    async def stream_handler(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        data = await reader.read(1024)
        logger.info(data)

        client_host, client_port, *_ = writer.get_extra_info("peername")

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

        if parsed_url.path == "":
            parsed_url = parsed_url._replace(path="/")

        req = Request(
            parsed_url=parsed_url,
            client_host=client_host,
            client_port=client_port,
        )

        # Check if there's router registered for the hostname
        if req.parsed_url.netloc in self._hostnames:
            router = self._hostnames[req.parsed_url.netloc]
        else:
            # Or use the default router
            router = self._default_router

        resp: Response
        matched_route, matched_params = router.match(req.parsed_url.path)
        if not matched_route:
            resp = NotFoundResponse()
        else:
            if matched_params is None:
                raise ValueError("Missing matched params")

            handler_params: dict[str, Any] = {}
            handler_params.update(matched_params)
            if matched_route.input_parameter and not parsed_url.query:
                if matched_route.input_parameter.annotation is Input:
                    resp = InputResponse(
                        matched_route.input_parameter.name,
                    )
                elif matched_route.input_parameter.annotation is SensitiveInput:
                    resp = SensitiveInputResponse(
                        matched_route.input_parameter.name,
                    )
                else:
                    raise ValueError(
                        "Unexpected input param type "
                        f"{matched_route.input_parameter.annotation}"
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

        writer.write(resp.as_bytes())
        await writer.drain()

        writer.close()

        return
