"""A small JSON service."""
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

STATE = {"ready": False}


async def startup():
    STATE["ready"] = True


async def health(request):
    return JSONResponse({"ready": STATE["ready"]})


app = Starlette(routes=[Route("/health", health)], on_startup=[startup])


@app.route("/items/{item_id:int}")
async def item(request):
    return JSONResponse({"id": request.path_params["item_id"]})


@app.exception_handler(404)
async def not_found(request, exc):
    return PlainTextResponse("nope", status_code=404)


@app.middleware("http")
async def add_header(request, call_next):
    response = await call_next(request)
    response.headers["x-service"] = "demo"
    return response
