"""Download the vendor documentation Cutoff depends on into docs/vendor/.

Stdlib only. Markdown sources are saved as-is; HTML pages are reduced to text.
Usage: python3 scripts/fetch_docs.py
"""
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "docs" / "vendor"
UA = {"User-Agent": "docs-reader"}

LINKUP = "https://docs.linkup.so/pages/"
ADAPTION = "https://docs.adaptionlabs.ai/"
DBX = "https://docs.databricks.com/aws/en/"

MARKDOWN = {
    "linkup": [LINKUP + p + ".md" for p in [
        "documentation/get-started/quickstart",
        "documentation/get-started/for-agents",
        "documentation/endpoints/search/overview",
        "documentation/endpoints/search/best-practices",
        "documentation/endpoints/search/for-agents",
        "documentation/endpoints/search/reference",
        "documentation/endpoints/fetch/overview",
        "documentation/endpoints/fetch/best-practices",
        "documentation/endpoints/fetch/reference",
        "documentation/platform/pricing",
        "documentation/platform/rate-limits",
        "documentation/platform/errors",
        "documentation/platform/authentication",
        "documentation/tutorials/structured-output-guide",
        "documentation/tutorials/filtering",
        "sdk/python/python",
        "integrations/mcp/mcp",
        "integrations/linkup-skill",
        "integrations/linkup-claude",
        "faq/faq",
    ]],
    "adaption": [ADAPTION + p + "/index.md" for p in [
        "introduction/getting-started",
        "introduction/create-api-keys",
        "adaptive-data-quickstart",
        "adaptive-data/overview",
        "adaptive-data/create-a-dataset",
        "adaptive-data/configure-adaptive-data",
        "adaptive-data/evaluate-dataset-quality",
        "adaptive-data/select-columns",
        "autoscientist-quickstart",
        "autoscientist/overview",
        "autoscientist/data-augmentation",
        "autoscientist/running-autoscientist",
        "autoscientist/interpreting-results",
        "autoscientist/download-the-model",
        "autoscientist/run-on-non-adapted-data",
        "autoscientist/supported-models",
        "autoscientist/recommended-hyperparameters",
        "runbooks/train-with-autoscientist",
        "runbooks/autoscientist-app-walkthrough",
        "inference-stacks/quickstart",
        "inference-stacks/key-concepts",
        "inference-stacks/generate-a-model-response",
        "inference-stacks/models",
        "tools/mcp",
        "tools/claude-plugin",
        "resources/faq",
        "api/resources/datasets/subresources/upload",
        "api/resources/datasets/methods/adapt",
        "api/resources/datasets/methods/run",
        "api/resources/datasets/methods/get_evaluation",
        "api/resources/datasets/subresources/custom_evals",
        "api/resources/autoscientist/methods/create",
        "api/resources/autoscientist/methods/get",
        "api/resources/autoscientist/methods/download",
        "api/resources/autoscientist/methods/recommend_hyperparams",
        "api/resources/responses/methods/create",
    ]],
}

HTML = {
    "databricks": [DBX + p for p in [
        "getting-started/free-edition-limitations",
        "mlflow3/genai/tracing/overview",
        "mlflow3/genai/getting-started/tracing/tracing-ide",
        "mlflow3/genai/tracing/integrations/anthropic",
        "mlflow3/genai/eval-monitor/",
        "mlflow3/genai/getting-started/eval",
        "mlflow3/genai/eval-monitor/custom-scorers",
        "mlflow3/genai/eval-monitor/evaluate-app",
        "mlflow3/genai/eval-monitor/concepts/scorers",
        "mlflow3/genai/recipes/set-up-coding-agent",
        "mlflow3/genai/recipes/set-up-mcp-server",
        "dev-tools/auth/pat",
        "dev-tools/python-sql-connector",
        "agents/mcp-tools/",
        "ai-search/ai-search/",
        "dev-tools/databricks-apps/",
    ]],
}


class ArticleText(HTMLParser):
    """Collect readable text from the <article> element of a docs page."""

    BLOCK = {"p", "div", "li", "tr", "br", "h1", "h2", "h3", "h4", "pre", "table", "ul", "ol"}
    SKIP = {"script", "style", "nav", "svg", "button"}

    def __init__(self):
        super().__init__()
        self.depth = 0
        self.skip = 0
        self.out = []

    def handle_starttag(self, tag, attrs):
        if tag == "article":
            self.depth += 1
        if not self.depth:
            return
        if tag in self.SKIP:
            self.skip += 1
        if tag in ("h1", "h2", "h3", "h4"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag == "pre":
            self.out.append("\n```\n")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag in self.BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        if tag == "pre":
            self.out.append("\n```\n")
        if tag == "article":
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and not self.skip:
            self.out.append(data)

    def text(self):
        return re.sub(r"\n{3,}", "\n\n", "".join(self.out)).strip()


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def slug(url, base):
    s = url[len(base):].strip("/")
    s = re.sub(r"(/index)?\.md$", "", s)
    return s.replace("/", "__") + ".md"


def main():
    failed = []
    for vendor, urls in MARKDOWN.items():
        base = LINKUP if vendor == "linkup" else ADAPTION
        d = ROOT / vendor
        d.mkdir(parents=True, exist_ok=True)
        for u in urls:
            try:
                body = get(u)
                (d / slug(u, base)).write_text(f"<!-- source: {u} -->\n\n{body}")
            except Exception as e:  # noqa: BLE001
                failed.append((u, str(e)))
    for vendor, urls in HTML.items():
        d = ROOT / vendor
        d.mkdir(parents=True, exist_ok=True)
        for u in urls:
            try:
                p = ArticleText()
                p.feed(get(u))
                body = p.text()
                if len(body) < 300:
                    raise ValueError("no article text")
                (d / slug(u, DBX)).write_text(f"<!-- source: {u} -->\n\n{body}\n")
            except Exception as e:  # noqa: BLE001
                failed.append((u, str(e)))
    for f in sorted(ROOT.rglob("*.md")):
        print(f"{f.stat().st_size:>8}  {f.relative_to(ROOT)}")
    for u, e in failed:
        print("FAILED", u, e, file=sys.stderr)


if __name__ == "__main__":
    main()
