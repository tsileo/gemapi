import asyncio
import ssl
from urllib.parse import urlparse


class Request:
    pass


class RawResponse:
    def __init__(self, status_code: int, meta: str, content: str) -> None:
        self.status_code = status_code
        self.meta = meta
        self.content = content


class Application:
    def __init__(self) -> None:
        self.routes = {}  # type: ignore

    def route(self, path: str):
        def _decorator(func):
            self.routes[path] = func
            return func

        return _decorator

    def _get_ssl_ctx(self) -> ssl.SSLContext:
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
        print(data)

        # Ensure it's a valid request
        # 'gemini://localhost/\r\n'
        # 1. ending with a <CR><LF>
        if not data.endswith(b"\r\n"):
            raise ValueError("Not ending with a CRLF")

        message = data.decode()
        parsed_url = urlparse(message[:-2])
        print(f"{parsed_url}")

        if parsed_url.scheme != "gemini":
            raise ValueError("Not a gemini URL")

        req = Request()
        resp = await self.routes["/"](req)

        data = f"{resp.status_code} {resp.meta}\r\n".encode("utf-8")
        writer.write(data)
        writer.write(resp.content.encode())
        await writer.drain()

        print("Close the connection")
        writer.close()

        return

    async def run(self):
        server = await asyncio.start_server(
            self._stream_handler, "127.0.0.1", 1965, ssl=self._get_ssl_ctx()
        )
        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        print(f"Serving on {addrs}")

        async with server:
            await server.serve_forever()
