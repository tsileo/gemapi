import asyncio
import datetime
import signal
import ssl

from loguru import logger

from gemapi.applications import Application
from gemapi.certificates import CertificateManager


class Server:
    def __init__(self, application: Application) -> None:
        self._application = application

    async def run(self, host: str = "localhost", port: int = 1965):
        cm = CertificateManager([host])
        loop = asyncio.get_event_loop()
        signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
        for s in signals:
            loop.add_signal_handler(
                s, lambda s=s: asyncio.create_task(self._shutdown(s, loop))
            )
        while True:
            cm.initialize()
            server = await asyncio.start_server(
                self._application.stream_handler, host, port, ssl=self._get_ssl_ctx(cm)
            )
            addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
            logger.info(f"Serving on {addrs}")
            stop = asyncio.Event()

            def restart_server():
                logger.info("Certificate is expiring, restarting server")
                stop.set()

            expires_in = (
                cm.certificate_expires_at().timestamp()
                - datetime.datetime.now(datetime.timezone.utc).timestamp()
            )
            logger.info(f"Certificate is expiring in {expires_in}")
            timer = loop.call_later(
                expires_in,
                restart_server,
            )

            try:
                await stop.wait()
            except asyncio.exceptions.CancelledError:
                logger.info("stop cancelled")
                break
            server.close()
            timer.cancel()

        logger.info("Exiting")

    def _get_ssl_ctx(self, cm: CertificateManager) -> ssl.SSLContext:
        # Only allow TLS 1.3
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.options |= (
            ssl.OP_NO_SSLv2
            & ssl.OP_NO_SSLv3
            & ssl.OP_NO_TLSv1
            & ssl.OP_NO_TLSv1_1
            & ssl.OP_NO_TLSv1_2
        )
        ssl_ctx.load_cert_chain(str(cm.certfile), keyfile=str(cm.keyfile))
        return ssl_ctx

    async def _shutdown(self, signal, loop):
        logger.info(f"Caught {signal=}")
        tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

        logger.info(f"Cancelling {len(tasks)} tasks")

        [task.cancel() for task in tasks]

        await asyncio.gather(*tasks)
        logger.info("stopping loop")
        loop.stop()
