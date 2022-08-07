import socket
from contextlib import contextmanager
from functools import wraps
from unittest import mock

import ignition  # type: ignore


@contextmanager
def mock_dns(hostnames):
    def _getaddrinfo(original_getaddrinfo):
        @wraps(original_getaddrinfo)
        def wrapper(*args, **kwargs):
            # ('example.com', 1965, 0, <SocketKind.SOCK_STREAM: 1>)/{}
            try:
                if args[0] in hostnames:
                    ip_address = "127.0.0.1"
                return [
                    (
                        socket.AF_INET,
                        socket.SOCK_STREAM,
                        6,
                        "",
                        (ip_address, args[1]),
                    )
                ]
            except KeyError:
                return original_getaddrinfo(*args, **kwargs)

        return wrapper

    with mock.patch("socket.getaddrinfo", _getaddrinfo(socket.getaddrinfo)):
        yield


def test_app(test_application):
    response = ignition.request("//localhost/")

    assert response.status == "20"
    assert response.data() == "toto"


def test_app__not_found(test_application):
    response = ignition.request("//localhost/not-found")

    assert response.status == "51"
    assert response.data() == "51 Not found"


def test_app__hello(test_application):
    response = ignition.request("//localhost/hello/thomas")

    assert response.status == "20"
    assert response.data() == "Hello thomas"


def test_app__input(test_application):
    response = ignition.request("//localhost/search")

    assert response.status == "10"
    assert response.data() == "q"


def test_app__input_with_value(test_application):
    response = ignition.request("//localhost/search?val")

    assert response.status == "20"
    assert response.data() == "val"


def test_app_hostname_route(test_application):
    with mock_dns({"example.com"}):
        response = ignition.request("//example.com/test")

    assert response.status == "20"
    assert response.data() == "example.com test"

    response = ignition.request("//localhost/test")
    assert response.status == "51"
