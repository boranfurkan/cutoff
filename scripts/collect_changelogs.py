"""Collect real release notes from GitHub and split them into changelog excerpts.

These excerpts become the prompts of the fine-tuning dataset: the model learns to turn
changelog prose into structured migration rules. Uses the logged-in `gh` CLI, so it costs
nothing beyond GitHub's API rate limit.

Usage: .venv/bin/python scripts/collect_changelogs.py [--per-repo 60]
Output: data/raw/changelog_chunks.jsonl
"""
import argparse
import hashlib
import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "changelog_chunks.jsonl"

# package name -> GitHub repo. Python libraries whose GitHub releases carry real notes.
REPOS = {
    "pydantic": "pydantic/pydantic",
    "fastapi": "fastapi/fastapi",
    "starlette": "encode/starlette",
    "httpx": "encode/httpx",
    "uvicorn": "encode/uvicorn",
    "sqlalchemy": "sqlalchemy/sqlalchemy",
    "alembic": "sqlalchemy/alembic",
    "flask": "pallets/flask",
    "werkzeug": "pallets/werkzeug",
    "click": "pallets/click",
    "jinja2": "pallets/jinja",
    "requests": "psf/requests",
    "urllib3": "urllib3/urllib3",
    "aiohttp": "aio-libs/aiohttp",
    "rich": "Textualize/rich",
    "textual": "Textualize/textual",
    "typer": "fastapi/typer",
    "attrs": "python-attrs/attrs",
    "pytest": "pytest-dev/pytest",
    "pytest-asyncio": "pytest-dev/pytest-asyncio",
    "numpy": "numpy/numpy",
    "pandas": "pandas-dev/pandas",
    "polars": "pola-rs/polars",
    "scipy": "scipy/scipy",
    "scikit-learn": "scikit-learn/scikit-learn",
    "matplotlib": "matplotlib/matplotlib",
    "pillow": "python-pillow/Pillow",
    "transformers": "huggingface/transformers",
    "datasets": "huggingface/datasets",
    "accelerate": "huggingface/accelerate",
    "peft": "huggingface/peft",
    "huggingface-hub": "huggingface/huggingface_hub",
    "torch": "pytorch/pytorch",
    "langchain": "langchain-ai/langchain",
    "langgraph": "langchain-ai/langgraph",
    "llama-index": "run-llama/llama_index",
    "openai": "openai/openai-python",
    "anthropic": "anthropics/anthropic-sdk-python",
    "mlflow": "mlflow/mlflow",
    "celery": "celery/celery",
    "redis": "redis/redis-py",
    "psycopg": "psycopg/psycopg",
    "pymongo": "mongodb/mongo-python-driver",
    "boto3": "boto/boto3",
    "marshmallow": "marshmallow-code/marshmallow",
    "structlog": "hynek/structlog",
    "loguru": "Delgan/loguru",
    "tqdm": "tqdm/tqdm",
    "black": "psf/black",
    "ruff": "astral-sh/ruff",
    "mypy": "python/mypy",
    "setuptools": "pypa/setuptools",
    "pip": "pypa/pip",
    "poetry": "python-poetry/poetry",
    "django-rest-framework": "encode/django-rest-framework",
    "dask": "dask/dask",
    "xarray": "pydata/xarray",
    "networkx": "networkx/networkx",
    "sentry-sdk": "getsentry/sentry-python",
    "gradio": "gradio-app/gradio",
    "streamlit": "streamlit/streamlit",
    "dspy": "stanfordnlp/dspy",
    "instructor": "567-labs/instructor",
    "litellm": "BerriAI/litellm",
    "chromadb": "chroma-core/chroma",
    "qdrant-client": "qdrant/qdrant-client",
    "playwright": "microsoft/playwright-python",
    "selenium": "SeleniumHQ/selenium",
    "websockets": "python-websockets/websockets",
    "grpcio": "grpc/grpc",
    "protobuf": "protocolbuffers/protobuf",
    "pyarrow": "apache/arrow",
}

MAX_CHARS = 3500
MIN_CHARS = 250
BREAKING = re.compile(
    r"breaking|deprecat|removed|remove |renamed|rename |no longer|replaced|drop(ped)? support|"
    r"migration|backwards?[- ]incompatible|api change|changed .* to ",
    re.I,
)


def gh_releases(repo: str, limit: int) -> list[dict]:
    pages = max(1, (limit + 99) // 100)
    out = []
    for page in range(1, pages + 1):
        r = subprocess.run(
            ["gh", "api", f"repos/{repo}/releases?per_page=100&page={page}"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode != 0:
            break
        batch = json.loads(r.stdout)
        out.extend(batch)
        if len(batch) < 100:
            break
    return out[:limit]


def split_sections(body: str) -> list[str]:
    """Split a release body on headings, then pack sections into chunks under MAX_CHARS."""
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S).strip()
    parts = re.split(r"\n(?=#{1,4} )", body)
    chunks, cur = [], ""
    for part in parts:
        if len(part) > MAX_CHARS:  # very long section: split on bullet boundaries
            lines, piece = part.split("\n"), ""
            for line in lines:
                if len(piece) + len(line) > MAX_CHARS and piece:
                    chunks.append(piece)
                    piece = ""
                piece += line + "\n"
            if piece:
                chunks.append(piece)
            continue
        if len(cur) + len(part) > MAX_CHARS and cur:
            chunks.append(cur)
            cur = ""
        cur += part + "\n"
    if cur:
        chunks.append(cur)
    return [c.strip() for c in chunks if len(c.strip()) >= MIN_CHARS]


def collect(package: str, repo: str, limit: int) -> list[dict]:
    try:
        releases = [r for r in gh_releases(repo, limit) if not r.get("draft") and (r.get("body") or "").strip()]
    except Exception:  # noqa: BLE001
        return []
    rows = []
    for i, rel in enumerate(releases):
        prev = releases[i + 1]["tag_name"] if i + 1 < len(releases) else None
        for j, chunk in enumerate(split_sections(rel["body"])):
            rows.append({
                "id": hashlib.sha1(f"{repo}|{rel['tag_name']}|{j}".encode()).hexdigest()[:12],
                "package": package,
                "repo": repo,
                "to_version": rel["tag_name"],
                "from_version": prev,
                "published_at": rel.get("published_at"),
                "prerelease": rel.get("prerelease", False),
                "source_url": rel["html_url"],
                "excerpt": chunk,
                "mentions_breaking": bool(BREAKING.search(chunk)),
            })
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-repo", type=int, default=60, help="max releases per repo")
    args = ap.parse_args()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda kv: (kv[0], collect(kv[0], kv[1], args.per_repo)), REPOS.items()))
    total = breaking = 0
    with OUT.open("w") as f:
        for package, rows in results:
            b = sum(r["mentions_breaking"] for r in rows)
            print(f"{package:24} {len(rows):5} chunks  {b:4} mention breaking changes")
            for r in rows:
                f.write(json.dumps(r) + "\n")
            total += len(rows)
            breaking += b
    print(f"\nTOTAL {total} chunks, {breaking} mention breaking changes -> {OUT}")


if __name__ == "__main__":
    main()
