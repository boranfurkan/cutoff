"""Live research through Linkup: find changelog pages and read them as markdown."""
import os

from linkup import LinkupClient

_client = None


def client() -> LinkupClient:
    global _client
    if _client is None:
        _client = LinkupClient(api_key=os.environ["LINKUP_API_KEY"])
    return _client


def search(query: str, max_results: int = 6, deep: bool = False) -> list[dict]:
    r = client().search(query=query, depth="deep" if deep else "standard",
                        output_type="searchResults", max_results=max_results)
    return [{"title": x.name, "url": x.url, "snippet": x.content[:500]}
            for x in r.results if getattr(x, "type", "text") == "text"]


def fetch(url: str) -> str:
    try:
        return client().fetch(url=url).markdown
    except Exception:  # noqa: BLE001  retry once with JS rendering for dynamic pages
        return client().fetch(url=url, render_js=True).markdown
