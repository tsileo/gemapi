# GemAPI

[![builds.sr.ht status](https://builds.sr.ht/~tsileo/gemapi.svg)](https://builds.sr.ht/~tsileo/gemapi?)

[Gemini](https://gemini.circumlunar.space/docs/specification.html) framework written in Python.

**Still in early development.**

## Features

 - Modern
   - as in it requires Python 3.10+
   - relies on type annotations (similar to FastAPI)
   - built on top of `asyncio` streams
 - Handle certificate generation
   - TLS 1.3 only with Ed22519 public key algorithm


## Getting started

```python
import asyncio

from gemapi.applications import Application
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


asyncio.run(app.run())
```
