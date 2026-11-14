import httpx

from client import api


def test_fetch_path():
    assert api.fetch_path("/invoices") == "/invoices"


def test_post_raw():
    assert api.post_raw("/invoices", "a,b") == 200


def test_proxied_client():
    c = api.proxied_client("http://localhost:3128")
    assert isinstance(c, httpx.Client)
    c.close()
