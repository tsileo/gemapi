import asyncio
import multiprocessing
import tempfile
import time

import ignition  # type: ignore
import pytest

from gemapi.server import Server

from .app import app


def run_app():
    asyncio.run(Server(app).run())


@pytest.fixture(scope="session")
def test_application():
    with tempfile.NamedTemporaryFile() as tmp_file:
        ignition.set_default_hosts_file(tmp_file.name)

        proc = multiprocessing.Process(target=run_app, args=())
        proc.start()
        time.sleep(1)
        yield app
        proc.terminate()
