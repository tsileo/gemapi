from gemapi.applications import Application
from gemapi.applications import Input
from gemapi.applications import Request
from gemapi.responses import Response

app = Application()

example_dot_com_router = app.router_for_hostname("example.com")


@app.route("/")
async def index(req: Request) -> Response:
    return Response(
        status_code=20,
        meta="text/gemini",
        body="toto",
    )


@app.route("/hello/{name:str}")
async def hello(req: Request, name: str) -> Response:
    return Response(
        status_code=20,
        meta="text/gemini",
        body=f"Hello {name}",
    )


@app.route("/search")
def search(req: Request, q: Input) -> Response:
    # Also support non coroutine functions
    return Response(
        status_code=20,
        meta="text/gemini",
        body=q.get_value(),
    )


@example_dot_com_router.route("/test")
def example_dot_com__test(req: Request) -> Response:
    return Response(
        status_code=20,
        meta="text/gemini",
        body="example.com test",
    )
