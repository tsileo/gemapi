from gemapi.applications import Application
from gemapi.applications import Input
from gemapi.applications import Request
from gemapi.responses import NotFoundError
from gemapi.responses import Response
from gemapi.responses import StatusCode

app = Application()

example_dot_com_router = app.router_for_hostname("example.com")


@app.route("/")
async def index(req: Request) -> Response:
    return Response(
        status_code=StatusCode.SUCCESS,
        meta="text/gemini",
        body="toto",
    )


@app.route("/hello/{name:str}")
async def hello(req: Request, name: str) -> Response:
    if name == "not-found":
        raise NotFoundError("nope")

    return Response(
        status_code=StatusCode.SUCCESS,
        meta="text/gemini",
        body=f"Hello {name}",
    )


@app.route("/search")
def search(req: Request, q: Input) -> Response:
    # Also support non coroutine functions
    return Response(
        status_code=StatusCode.SUCCESS,
        meta="text/gemini",
        body=q.get_value(),
    )


@example_dot_com_router.route("/test")
def example_dot_com__test(req: Request) -> Response:
    return Response(
        status_code=StatusCode.SUCCESS,
        meta="text/gemini",
        body="example.com test",
    )
