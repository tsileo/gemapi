import asyncio
import importlib

import click

from gemapi.applications import Application
from gemapi.server import Server


@click.group()
def main():
    pass


@click.command()
@click.argument("app")
def run(app: str) -> None:
    mod, attr = app.split(":")
    application = getattr(importlib.import_module(mod), attr)
    if not isinstance(application, Application):
        raise ValueError(f"{app} is not a valid app")

    asyncio.run(Server(application).run(), debug=True)


main.add_command(run)
