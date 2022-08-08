import inspect
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from typing import Callable

from gemapi.request import Input
from gemapi.request import SensitiveInput

_PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")


class PathParamMatcher(Enum):
    STR = "str"


_PATH_PARAM_MATCHERS = {
    PathParamMatcher.STR: "[^/]+",
}


@dataclass(frozen=True)
class PathParam:
    name: str
    matcher: PathParamMatcher


@dataclass(frozen=True)
class Route:
    path_regex: re.Pattern
    path_params: list[PathParam]
    handler_signature: inspect.Signature
    input_parameter: inspect.Parameter | None
    handler: Callable[..., Any]
    handler_is_coroutine: bool

    @classmethod
    def from_path(cls, path: str, handler: Callable[..., Any]) -> "Route":
        path_regex, path_params = _build_path_regex(path)
        func_sig = inspect.signature(handler)
        maybe_input_param: inspect.Parameter | None = None

        for path_param in path_params:
            if path_param.name not in func_sig.parameters:
                raise ValueError(
                    f"{handler.__name__} is missing a {path_param.name} " "parameter"
                )

        for param in func_sig.parameters.values():
            if param.annotation is Input or param.annotation is SensitiveInput:
                if maybe_input_param is None:
                    maybe_input_param = param
                else:
                    raise ValueError(
                        f"{handler.__name__}: Only 1 Input/SensitiveInput "
                        "parameter is allowed"
                    )

        return cls(
            path_regex=path_regex,
            path_params=path_params,
            handler_signature=func_sig,
            input_parameter=maybe_input_param,
            handler=handler,
            handler_is_coroutine=inspect.iscoroutinefunction(handler),
        )


def _build_path_regex(path: str) -> tuple[re.Pattern, list[PathParam]]:
    # TODO: detect duplicate params and error on invalid matcher
    path_params = []

    replacements = []
    for matched_param in _PARAM_REGEX.finditer(path):
        matcher = PathParamMatcher.STR
        group = matched_param.group()
        parts = group.split(":")

        match parts:
            case [param_name]:
                name = param_name[1:-1]
            case [raw_name, raw_matcher]:
                name = raw_name[1:]
                matcher = PathParamMatcher(raw_matcher[:-1])
            case _:
                raise ValueError(f"Unexpected parts {parts}")

        matcher_regex = _PATH_PARAM_MATCHERS[matcher]
        replacements.append((group, f"(?P<{name}>{matcher_regex})"))
        path_params.append(PathParam(name=name, matcher=matcher))

    for group, replacement in replacements:
        path = path.replace(group, replacement)
    return re.compile(path + "$"), path_params


class Router:
    def __init__(self) -> None:
        self._routes: list[Route] = []

    def route(self, path: str) -> Callable[..., Any]:
        def _decorator(handler: Callable[..., Any]) -> Callable[..., Any]:
            route = Route.from_path(path, handler)
            self._routes.append(route)
            return handler

        return _decorator

    def match(self, path: str) -> tuple[Route | None, dict[str, str] | None]:
        for route in self._routes:
            if m := route.path_regex.match(path):
                return route, m.groupdict()

        return None, None
