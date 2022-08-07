# GemAPI

[![builds.sr.ht status](https://builds.sr.ht/~tsileo/gemapi.svg)](https://builds.sr.ht/~tsileo/gemapi?)

[Gemini](https://gemini.circumlunar.space/docs/specification.html) framework written in Python.

**Still in early development, there's no releases yet**


## Features

 - Modern
   - as in it requires Python 3.10+
   - relies on type annotations (similar to FastAPI)
   - built on top of `asyncio` streams
 - Handle certificate generation and renewal
   - TLS 1.3 only with Ed25519 public key algorithm
   - Certificate is renewed automatically on expiration


## Getting started

```python
import asyncio

from gemapi.applications import Application
from gemapi.request import Input
from gemapi.request import Request
from gemapi.responses import Response
from gemapi.server import Server

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


asyncio.run(Server(app).run())
```


## Contributing

All the development takes place on [sourcehut](https://git.sr.ht/~tsileo/gemapi), GitHub is only used as a mirror:

 - [Project](https://sr.ht/~tsileo/gemapi/)
 - [Issue tracker](https://todo.sr.ht/~tsileo/gemapi)
 - [Mailing list](https://sr.ht/~tsileo/gemapi/lists)

Contributions are welcomed.


## License

The project is licensed under the ISC LICENSE (see the LICENSE file).
