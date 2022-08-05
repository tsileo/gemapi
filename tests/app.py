from gemapi.applications import Application
from gemapi.applications import RawResponse
from gemapi.applications import Request

app = Application()


@app.route("/")
async def hello(req: Request) -> RawResponse:
    return RawResponse(
        status_code=20,
        meta="text/gemini",
        content="toto",
    )
