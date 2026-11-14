"""Query-filter and settings helpers for the catalogue service."""
from starlette.config import Config
from starlette.datastructures import QueryParams


def same_filters(query_a: str, query_b: str) -> bool:
    """True when two query strings select the same filters.

    The order in which a client repeats a key (``tag=a&tag=b`` vs ``tag=b&tag=a``) must not matter:
    both select the same set of products, so cached results can be shared.
    """
    return QueryParams(query_a) == QueryParams(query_b)


def tags(query: str) -> list[str]:
    return sorted(QueryParams(query).getlist("tag"))


def load_banner(env_file: str) -> str:
    """Read BANNER from an env file and return the bare text.

    Operators wrap the value in quotes, sometimes doubly (``BANNER="'Sale now on'"``) after copying it
    from a shell script. The banner shown to customers must never contain those wrapping quotes.
    """
    return Config(env_file)("BANNER", default="")
