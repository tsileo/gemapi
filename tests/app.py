from gemapi.applications import Application
from gemapi.applications import Input
from gemapi.applications import Request
from gemapi.applications import Response

app = Application()


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
