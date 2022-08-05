import ignition  # type: ignore


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
