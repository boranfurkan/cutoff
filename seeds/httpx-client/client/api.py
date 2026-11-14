"""HTTP client wrapper for the billing service."""
import httpx


def wsgi_app(environ, start_response):
    start_response("200 OK", [("Content-Type", "application/json")])
    return [b'{"path": "' + environ["PATH_INFO"].encode() + b'"}']


def make_client(proxy_url=None):
    proxies = {"all://": proxy_url} if proxy_url else None
    return httpx.Client(app=wsgi_app, base_url="http://billing.test", proxies=proxies, timeout=5)


def fetch_path(path):
    with make_client() as c:
        return c.get(path).json()["path"]


def post_raw(path, text):
    with make_client() as c:
        return c.post(path, data=text.encode()).status_code


def proxied_client(proxy_url):
    return httpx.Client(proxies=proxy_url)
