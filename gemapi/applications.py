import asyncio
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from gemapi.request import Input
from gemapi.request import Request
from gemapi.request import SensitiveInput
from gemapi.responses import BadRequestError
from gemapi.responses import BadRequestResponse
from gemapi.responses import InputResponse
from gemapi.responses import NotFoundError
from gemapi.responses import Response
from gemapi.responses import SensitiveInputResponse
from gemapi.responses import StatusError
from gemapi.responses import TemporaryFailureResponse
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
        client_host, client_port, *_ = writer.get_extra_info("peername")
        resp: Response

        try:
            data = await reader.read(1026)

            # Ensure it's a valid request
            # 'gemini://localhost/\r\n'
            # 1. ending with a <CR><LF>
            if not data.endswith(b"\r\n"):
                raise BadRequestError("Not ending with a CRLF")

            message = data.decode()

            parsed_url = urlparse(message[:-2])

            if parsed_url.scheme != "gemini":
                raise BadRequestError(f"Invalid scheme {parsed_url.scheme}")

            if parsed_url.path == "":
                parsed_url = parsed_url._replace(path="/")

            if "." in parsed_url.path:
                raise BadRequestError("dots in path are not allowed")

        except StatusError as status_error:
            logger.error(f"{client_host}:{client_port} - {status_error.data()}")
            resp = status_error.as_response()
        except Exception:
            logger.exception(f"{client_host}:{client_port} - 51")
            resp = BadRequestResponse("Bad request")

        else:
            req = Request(
                parsed_url=parsed_url,
                client_host=client_host,
                client_port=client_port,
            )

            try:
                resp = await self._process_request(req)
            except StatusError as status_error:
                logger.error(
                    f"{client_host}:{client_port} - {req.parsed_url.geturl()} "
                    f"{status_error.data()}"
                )
                resp = status_error.as_response()
            except Exception:
                resp = TemporaryFailureResponse("Failed to process request")
                logger.exception(
                    f"{client_host}:{client_port} - "
                    f"{req.parsed_url.geturl()} {resp.status_code.name} "
                    f"{resp.status_code.value} {resp.meta}"
                )
            else:
                logger.info(
                    f"{client_host}:{client_port} - "
                    f"{req.parsed_url.geturl()} {resp.status_code.name} "
                    f"{resp.status_code.value} {resp.meta}"
                )

        writer.write(resp.as_bytes())
        await writer.drain()
        writer.close()

        return

    async def _process_request(
        self,
        req: Request,
    ) -> Response:
        # Check if there's router registered for the hostname
        if req.parsed_url.netloc in self._hostnames:
            router = self._hostnames[req.parsed_url.netloc]
        else:
            # Or use the default router
            router = self._default_router

        # Select the router
        resp: Response
        matched_route, matched_params = router.match(req.parsed_url.path)

        # Build the response
        if not matched_route:
            raise NotFoundError("Not found")

        if matched_params is None:
            raise ValueError("Missing matched params")

        handler_params: dict[str, Any] = {}
        handler_params.update(matched_params)
        if matched_route.input_parameter and not req.parsed_url.query:
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
                    req.parsed_url.query
                )
            # TODO: pass the path params wit the right type as kwargs
            if matched_route.handler_is_coroutine:
                resp = await matched_route.handler(req, **handler_params)
            else:
                resp = matched_route.handler(req, **handler_params)

        return resp
