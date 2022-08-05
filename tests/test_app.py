import ignition  # type: ignore


def test_app(test_application):
    response = ignition.request("//localhost/")

    assert response.status == "20"
    assert response.data() == "toto"
