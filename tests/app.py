from gemapi.applications import Application
from gemapi.applications import Input
from gemapi.applications import RawResponse
from gemapi.applications import Request

app = Application()


@app.route("/")
async def index(req: Request) -> RawResponse:
    return RawResponse(
        status_code=20,
        meta="text/gemini",
        content="toto",
    )


@app.route("/hello/{name:str}")
async def hello(req: Request, name: str) -> RawResponse:
    return RawResponse(
        status_code=20,
        meta="text/gemini",
        content=f"Hello {name}",
    )


@app.route("/search")
async def search(req: Request, q: Input) -> RawResponse:
    return RawResponse(
        status_code=20,
        meta="text/gemini",
        content=q.get_value(),
    )
