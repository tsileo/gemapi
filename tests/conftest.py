import asyncio
import multiprocessing
import tempfile
import time

import ignition  # type: ignore
import pytest

from gemapi.certificates import build_certificate

from .app import app


def run_app():
    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.run())


@pytest.fixture(scope="session")
def test_application():
    with tempfile.NamedTemporaryFile() as tmp_file:
        ignition.set_default_hosts_file(tmp_file.name)

        build_certificate("localhost")
        proc = multiprocessing.Process(target=run_app, args=())
        proc.start()
        time.sleep(1)
        yield app
        proc.terminate()
