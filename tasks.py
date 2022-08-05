from typing import Optional

from invoke import Context  # type: ignore
from invoke import run  # type: ignore
from invoke import task  # type: ignore


@task
def autoformat(ctx):
    # type: (Context) -> None
    run("black .", echo=True)
    run("isort -sl .", echo=True)


@task
def lint(ctx):
    # type: (Context) -> None
    run("black --check .", echo=True)
    run("isort -sl --check-only .", echo=True)
    run("flake8 .", echo=True)
    run("mypy .", echo=True)


@task
def tests(ctx, k=None):
    # type: (Context, Optional[str]) -> None
    pytest_args = " -vvv"
    if k:
        pytest_args += f" -k {k}"
    run(
        f"pytest tests{pytest_args}",
        pty=True,
        echo=True,
    )
